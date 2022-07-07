import ape
import pytest
from utils import actions
from utils.constants import DAY


@pytest.fixture(autouse=True)
def seed_vault_with_funds(mint_and_deposit_into_vault, vault, gov):
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)


@pytest.mark.parametrize("max_debt", [0, 10**22])
def test_update_max_debt__with_debt_value(gov, vault, strategy, max_debt):
    vault.updateMaxDebtForStrategy(strategy.address, max_debt, sender=gov)

    assert vault.strategies(strategy.address).maxDebt == max_debt


def test_update_max_debt__with_inactive_strategy(gov, vault, create_strategy):
    strategy = create_strategy(vault)
    max_debt = 10**18

    with ape.reverts("inactive strategy"):
        vault.updateMaxDebtForStrategy(strategy.address, max_debt, sender=gov)


def test_update_debt__without_permission__reverts():
    # TODO: implement after access control for update debt is complete
    pass


def test_update_debt__with_current_debt_less_than_new_debt(gov, asset, vault, strategy):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2
    current_debt = vault.strategies(strategy.address).currentDebt
    difference = new_debt - current_debt
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    vault.updateMaxDebtForStrategy(strategy.address, new_debt, sender=gov)

    tx = vault.updateDebt(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].currentDebt == current_debt
    assert event[0].newDebt == new_debt

    assert vault.strategies(strategy.address).currentDebt == new_debt
    assert asset.balanceOf(strategy) == new_debt
    assert asset.balanceOf(vault) == (vault_balance - new_debt)
    assert vault.totalIdle() == initial_idle - difference
    assert vault.totalDebt() == initial_debt + difference


def test_update_debt__with_current_debt_equal_to_new_debt__reverts(
    gov, asset, vault, strategy
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2

    actions.add_debt_to_strategy(gov, strategy, vault, new_debt)

    with ape.reverts("new debt equals current debt"):
        vault.updateDebt(strategy.address, sender=gov)


def test_update_debt__with_current_debt_greater_than_new_debt_and_zero_withdrawable__reverts(
    gov, asset, vault, locked_strategy
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    new_debt = vault_balance // 2

    actions.add_debt_to_strategy(gov, locked_strategy, vault, current_debt)
    # lock funds to set withdrawable to zero
    locked_strategy.setLockedFunds(current_debt, DAY, sender=gov)
    # reduce debt in strategy
    vault.updateMaxDebtForStrategy(locked_strategy.address, new_debt, sender=gov)

    with ape.reverts("nothing to withdraw"):
        vault.updateDebt(locked_strategy.address, sender=gov)


def test_update_debt__with_current_debt_greater_than_new_debt_and_insufficient_withdrawable(
    gov, asset, vault, locked_strategy
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    locked_debt = current_debt // 2
    new_debt = vault_balance // 4
    difference = current_debt - locked_debt  # maximum we can withdraw

    actions.add_debt_to_strategy(gov, locked_strategy, vault, current_debt)

    # reduce debt in strategy
    vault.updateMaxDebtForStrategy(locked_strategy.address, new_debt, sender=gov)
    # lock portion of funds to reduce withdrawable
    locked_strategy.setLockedFunds(locked_debt, DAY, sender=gov)
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    tx = vault.updateDebt(locked_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == locked_strategy.address
    assert event[0].currentDebt == current_debt
    assert event[0].newDebt == locked_debt

    assert vault.strategies(locked_strategy.address).currentDebt == locked_debt
    assert asset.balanceOf(locked_strategy) == locked_debt
    assert asset.balanceOf(vault) == (vault_balance - locked_debt)
    assert vault.totalIdle() == initial_idle + difference
    assert vault.totalDebt() == initial_debt - difference


def test_update_debt__with_current_debt_greater_than_new_debt_and_sufficient_withdrawable(
    gov, asset, vault, strategy
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    new_debt = vault_balance // 2
    difference = current_debt - new_debt

    actions.add_debt_to_strategy(gov, strategy, vault, current_debt)
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # reduce debt in strategy
    vault.updateMaxDebtForStrategy(strategy.address, new_debt, sender=gov)

    tx = vault.updateDebt(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].currentDebt == current_debt
    assert event[0].newDebt == new_debt

    assert vault.strategies(strategy.address).currentDebt == new_debt
    assert asset.balanceOf(strategy) == new_debt
    assert asset.balanceOf(vault) == (vault_balance - new_debt)
    assert vault.totalIdle() == initial_idle + difference
    assert vault.totalDebt() == initial_debt - difference


def test_update_debt__with_new_debt_greater_than_max_desired_debt(
    gov, asset, vault, strategy
):
    vault_balance = asset.balanceOf(vault)
    max_debt = vault_balance
    max_desired_debt = vault_balance // 2
    current_debt = vault.strategies(strategy.address).currentDebt
    difference = max_desired_debt - current_debt
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    vault.updateMaxDebtForStrategy(strategy.address, max_debt, sender=gov)
    strategy.setMaxDebt(max_desired_debt, sender=gov)

    # update debt
    tx = vault.updateDebt(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].currentDebt == current_debt
    assert event[0].newDebt == max_desired_debt

    assert vault.strategies(strategy.address).currentDebt == max_desired_debt
    assert asset.balanceOf(strategy) == max_desired_debt
    assert asset.balanceOf(vault) == (vault_balance - max_desired_debt)
    assert vault.totalIdle() == initial_idle - difference
    assert vault.totalDebt() == initial_debt + difference


def test_update_debt__with_new_debt_less_than_min_desired_debt__reverts(
    gov, asset, vault, strategy
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance // 2
    new_debt = vault_balance
    min_desired_debt = vault_balance * 2

    # set existing debt
    actions.add_debt_to_strategy(gov, strategy, vault, current_debt)

    # set new max debt lower than min debt
    vault.updateMaxDebtForStrategy(strategy.address, new_debt, sender=gov)
    strategy.setMinDebt(min_desired_debt, sender=gov)

    with ape.reverts("new debt less than min debt"):
        vault.updateDebt(strategy.address, sender=gov)


@pytest.mark.parametrize("minimum_total_idle", [0, 10**21])
def test_set_minimum_total_idle__with_minimum_total_idle(
    gov, vault, minimum_total_idle
):

    tx = vault.setMinimumTotalIdle(minimum_total_idle, sender=gov)
    assert vault.minimumTotalIdle() == minimum_total_idle

    event = list(tx.decode_logs(vault.UpdateMinimumTotalIdle))
    assert len(event) == 1
    assert event[0].minimumTotalIdle == minimum_total_idle


@pytest.mark.parametrize("minimum_total_idle", [10**21])
def test_set_minimum_total_idle__without_permission__reverts(
    accounts, vault, minimum_total_idle
):
    """
    Only DEBT_MANAGER should be able to update minimumTotalIdle. Reverting if found any other sender.
    """
    with ape.reverts():
        vault.setMinimumTotalIdle(minimum_total_idle, sender=accounts[-1])


def test_update_debt__with_current_debt_less_than_new_debt_and_minimum_total_idle(
    gov, asset, vault, strategy
):
    """
    Current debt is greater than new debt. Vault has a minimum total idle value small that does not affect the updateDebt method.
    """
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2
    current_debt = vault.strategies(strategy.address).currentDebt
    difference = new_debt - current_debt
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # set minimum total idle to a small value that doesn´t interfeer on updateDebt
    minimum_total_idle = 1
    vault.setMinimumTotalIdle(minimum_total_idle, sender=gov)
    assert vault.minimumTotalIdle() == 1

    # increase debt in strategy
    vault.updateMaxDebtForStrategy(strategy.address, new_debt, sender=gov)

    tx = vault.updateDebt(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].currentDebt == current_debt
    assert event[0].newDebt == new_debt

    assert vault.strategies(strategy.address).currentDebt == new_debt
    assert asset.balanceOf(strategy) == new_debt
    assert asset.balanceOf(vault) == (vault_balance - new_debt)
    assert vault.totalIdle() == initial_idle - difference
    assert vault.totalDebt() == initial_debt + difference

    assert vault.totalIdle() > vault.minimumTotalIdle()


def test_update_debt__with_current_debt_less_than_new_debt_and_total_idle_lower_than_minimum_total_idle__revert(
    gov, asset, vault, strategy
):
    """
    Current debt is greater than new debt. Vault has a total idle value lower/equal to minimum total idle value. It cannot provide more
    assets to the strategy as there are no funds, we are therefore reverting.
    """

    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2

    minimum_total_idle = vault.totalIdle()
    vault.setMinimumTotalIdle(minimum_total_idle, sender=gov)
    assert vault.minimumTotalIdle() == vault.totalIdle()

    # increase debt in strategy
    vault.updateMaxDebtForStrategy(strategy.address, new_debt, sender=gov)

    with ape.reverts("no funds to deposit"):
        vault.updateDebt(strategy.address, sender=gov)


def test_update_debt__with_current_debt_less_than_new_debt_and_minimum_total_idle_reducing_new_debt(
    gov, asset, vault, strategy
):
    """
    Current debt is lower than new debt. Value of minimum total idle reduces the amount of assets that the vault can provide.
    """

    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    current_debt = vault.strategies(strategy.address).currentDebt

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # we ensure a small amount of liquidity remains in the vault
    minimum_total_idle = vault_balance - 1
    vault.setMinimumTotalIdle(minimum_total_idle, sender=gov)
    assert vault.minimumTotalIdle() == vault_balance - 1

    # vault can give as much as it reaches minimum_total_idle
    expected_new_differnce = initial_idle - minimum_total_idle
    expected_new_debt = current_debt + expected_new_differnce

    # increase debt in strategy
    vault.updateMaxDebtForStrategy(strategy.address, new_debt, sender=gov)

    tx = vault.updateDebt(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].currentDebt == current_debt
    assert event[0].newDebt == expected_new_debt

    assert vault.strategies(strategy.address).currentDebt == expected_new_debt
    assert asset.balanceOf(strategy) == expected_new_debt
    assert asset.balanceOf(vault) == vault_balance - expected_new_differnce
    assert vault.totalIdle() == initial_idle - expected_new_differnce
    assert vault.totalDebt() == initial_debt + expected_new_differnce


def test_update_debt__with_current_debt_greater_than_new_debt_and_minimum_total_idle(
    gov, asset, vault, strategy
):
    """
    Current debt is greater than new debt. Vault has a minimum total idle value small that does not affect the updateDebt method.
    """
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    new_debt = vault_balance // 2
    difference = current_debt - new_debt

    actions.add_debt_to_strategy(gov, strategy, vault, current_debt)

    # we compute vault values again, as they have changed
    vault_balance = asset.balanceOf(vault)
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # small minimum total idle value not to interfeer with updateDebt method
    minimum_total_idle = 1
    vault.setMinimumTotalIdle(minimum_total_idle, sender=gov)

    assert vault.minimumTotalIdle() == 1

    # reduce debt in strategy
    vault.updateMaxDebtForStrategy(strategy.address, new_debt, sender=gov)

    tx = vault.updateDebt(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].currentDebt == current_debt
    assert event[0].newDebt == new_debt

    assert vault.strategies(strategy.address).currentDebt == new_debt
    assert asset.balanceOf(strategy) == new_debt
    assert asset.balanceOf(vault) == vault_balance + difference
    assert vault.totalIdle() == initial_idle + difference
    assert vault.totalDebt() == initial_debt - difference


def test_update_debt__with_current_debt_greater_than_new_debt_and_total_idle_less_than_minimum_total_idle(
    gov, asset, vault, strategy
):
    """
    Current debt is greater than new debt. Vault has a total idle value lower than its minimum total idle value.
    .updateDebt will reduce the new debt value to increase the amount of assets that its getting from the strategy and ensure that
    total idle value is greater than minimum total idle.
    """
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    new_debt = vault_balance // 3

    actions.add_debt_to_strategy(gov, strategy, vault, current_debt)

    # we compute vault values again, as they have changed
    vault_balance = asset.balanceOf(vault)
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # we set minimum total idle to a value greater than debt difference
    minimum_total_idle = current_debt - new_debt + 1
    vault.setMinimumTotalIdle(minimum_total_idle, sender=gov)
    assert vault.minimumTotalIdle() == current_debt - new_debt + 1

    # we compute expected changes in debt due to minimum total idle need
    expected_new_difference = minimum_total_idle - initial_idle
    expected_new_debt = current_debt - expected_new_difference

    # reduce debt in strategy
    vault.updateMaxDebtForStrategy(strategy.address, new_debt, sender=gov)

    tx = vault.updateDebt(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].currentDebt == current_debt
    assert event[0].newDebt == expected_new_debt

    assert vault.strategies(strategy.address).currentDebt == expected_new_debt
    assert asset.balanceOf(strategy) == expected_new_debt
    assert asset.balanceOf(vault) == vault_balance + expected_new_difference
    assert vault.totalIdle() == initial_idle + expected_new_difference
    assert vault.totalDebt() == initial_debt - expected_new_difference
