import pytest
import ape
from utils import actions
from utils.constants import DAY


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
