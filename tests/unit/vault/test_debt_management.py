import ape
import pytest
from utils.constants import DAY


@pytest.fixture(autouse=True)
def seed_vault_with_funds(mint_and_deposit_into_vault, vault, gov):
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)


@pytest.mark.parametrize("max_debt", [0, 10**22])
def test_update_max_debt__with_debt_value(gov, vault, strategy, max_debt):
    vault.update_max_debt_for_strategy(strategy.address, max_debt, sender=gov)

    assert vault.strategies(strategy.address).max_debt == max_debt


def test_update_max_debt__with_inactive_strategy(gov, vault, create_strategy):
    strategy = create_strategy(vault)
    max_debt = 10**18

    with ape.reverts("inactive strategy"):
        vault.update_max_debt_for_strategy(strategy.address, max_debt, sender=gov)


def test_update_debt__without_permission__reverts(gov, vault, asset, strategy, bunny):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2
    current_debt = vault.strategies(strategy.address).current_debt

    vault.update_max_debt_for_strategy(strategy.address, new_debt, sender=gov)
    with ape.reverts():
        vault.update_debt(strategy.address, new_debt, sender=bunny)


def test_update_debt__with_strategy_max_debt_less_than_new_debt(
    gov, asset, vault, strategy
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2

    vault.update_max_debt_for_strategy(strategy.address, new_debt, sender=gov)

    tx = vault.update_debt(strategy.address, new_debt + 10, sender=gov)

    assert tx.return_value == new_debt

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == 0
    assert event[0].new_debt == new_debt

    assert vault.strategies(strategy.address).current_debt == new_debt
    assert asset.balanceOf(strategy) == new_debt
    assert asset.balanceOf(vault) == vault_balance - new_debt
    assert vault.totalIdle() == vault_balance - new_debt
    assert vault.totalDebt() == new_debt


def test_update_debt__with_current_debt_less_than_new_debt(gov, asset, vault, strategy):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2
    current_debt = vault.strategies(strategy.address).current_debt
    difference = new_debt - current_debt
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    vault.update_max_debt_for_strategy(strategy.address, new_debt, sender=gov)

    tx = vault.update_debt(strategy.address, new_debt, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    assert vault.strategies(strategy.address).current_debt == new_debt
    assert asset.balanceOf(strategy) == new_debt
    assert asset.balanceOf(vault) == (vault_balance - new_debt)
    assert vault.totalIdle() == initial_idle - difference
    assert vault.totalDebt() == initial_debt + difference


def test_update_debt__with_current_debt_equal_to_new_debt__reverts(
    gov, asset, vault, strategy, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2

    add_debt_to_strategy(gov, strategy, vault, new_debt)

    with ape.reverts("new debt equals current debt"):
        vault.update_debt(strategy.address, new_debt, sender=gov)


def test_update_debt__with_current_debt_greater_than_new_debt_and_zero_withdrawable(
    gov, asset, vault, locked_strategy, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    new_debt = vault_balance // 2

    add_debt_to_strategy(gov, locked_strategy, vault, current_debt)
    # lock funds to set withdrawable to zero
    locked_strategy.setLockedFunds(current_debt, DAY, sender=gov)
    # reduce debt in strategy
    vault.update_max_debt_for_strategy(locked_strategy.address, new_debt, sender=gov)

    tx = vault.update_debt(locked_strategy.address, new_debt, sender=gov)

    assert tx.return_value == current_debt


def test_update_debt__with_current_debt_greater_than_new_debt_and_strategy_has_losses__reverts(
    gov, asset, vault, lossy_strategy, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    new_debt = vault_balance // 2
    loss = int(vault_balance * 0.1)

    add_debt_to_strategy(gov, lossy_strategy, vault, current_debt)

    lossy_strategy.setLoss(gov, loss, sender=gov)

    with ape.reverts("strategy has unrealised losses"):
        vault.update_debt(lossy_strategy.address, new_debt, sender=gov)


def test_update_debt__with_current_debt_greater_than_new_debt_and_insufficient_withdrawable(
    gov, asset, vault, locked_strategy, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    locked_debt = current_debt // 2
    new_debt = vault_balance // 4
    difference = current_debt - locked_debt  # maximum we can withdraw

    add_debt_to_strategy(gov, locked_strategy, vault, current_debt)

    # reduce debt in strategy
    vault.update_max_debt_for_strategy(locked_strategy.address, new_debt, sender=gov)
    # lock portion of funds to reduce withdrawable
    locked_strategy.setLockedFunds(locked_debt, DAY, sender=gov)
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    tx = vault.update_debt(locked_strategy.address, new_debt, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == locked_strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == locked_debt

    assert vault.strategies(locked_strategy.address).current_debt == locked_debt
    assert asset.balanceOf(locked_strategy) == locked_debt
    assert asset.balanceOf(vault) == (vault_balance - locked_debt)
    assert vault.totalIdle() == initial_idle + difference
    assert vault.totalDebt() == initial_debt - difference


def test_update_debt__with_current_debt_greater_than_new_debt_and_sufficient_withdrawable(
    gov, asset, vault, strategy, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    new_debt = vault_balance // 2
    difference = current_debt - new_debt

    add_debt_to_strategy(gov, strategy, vault, current_debt)
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()
    # reduce debt in strategy
    vault.update_max_debt_for_strategy(strategy.address, new_debt, sender=gov)

    tx = vault.update_debt(strategy.address, new_debt, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    assert vault.strategies(strategy.address).current_debt == new_debt
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
    current_debt = vault.strategies(strategy.address).current_debt
    difference = max_desired_debt - current_debt
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    vault.update_max_debt_for_strategy(strategy.address, max_debt, sender=gov)
    strategy.setMaxDebt(max_desired_debt, sender=gov)

    # update debt
    tx = vault.update_debt(strategy.address, max_debt, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == max_desired_debt

    assert vault.strategies(strategy.address).current_debt == max_desired_debt
    assert asset.balanceOf(strategy) == max_desired_debt
    assert asset.balanceOf(vault) == (vault_balance - max_desired_debt)
    assert vault.totalIdle() == initial_idle - difference
    assert vault.totalDebt() == initial_debt + difference


@pytest.mark.parametrize("minimum_total_idle", [0, 10**21])
def test_set_minimum_total_idle__with_minimum_total_idle(
    gov, vault, minimum_total_idle
):

    tx = vault.set_minimum_total_idle(minimum_total_idle, sender=gov)
    assert vault.minimum_total_idle() == minimum_total_idle

    event = list(tx.decode_logs(vault.UpdateMinimumTotalIdle))
    assert len(event) == 1
    assert event[0].minimum_total_idle == minimum_total_idle


@pytest.mark.parametrize("minimum_total_idle", [10**21])
def test_set_minimum_total_idle__without_permission__reverts(
    accounts, vault, minimum_total_idle
):
    """
    Only DEBT_MANAGER should be able to update minimum_total_idle. Reverting if found any other sender.
    """
    with ape.reverts():
        vault.set_minimum_total_idle(minimum_total_idle, sender=accounts[-1])


def test_update_debt__with_current_debt_less_than_new_debt_and_minimum_total_idle(
    gov, asset, vault, strategy
):
    """
    Current debt is greater than new debt. Vault has a minimum total idle value small that does not affect the update_debt method.
    """
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2
    current_debt = vault.strategies(strategy.address).current_debt
    difference = new_debt - current_debt
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # set minimum total idle to a small value that doesn´t interfeer on update_debt
    minimum_total_idle = 1
    vault.set_minimum_total_idle(minimum_total_idle, sender=gov)
    assert vault.minimum_total_idle() == 1

    # increase debt in strategy
    vault.update_max_debt_for_strategy(strategy.address, new_debt, sender=gov)

    tx = vault.update_debt(strategy.address, new_debt, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    assert vault.strategies(strategy.address).current_debt == new_debt
    assert asset.balanceOf(strategy) == new_debt
    assert asset.balanceOf(vault) == (vault_balance - new_debt)
    assert vault.totalIdle() == initial_idle - difference
    assert vault.totalDebt() == initial_debt + difference

    assert vault.totalIdle() > vault.minimum_total_idle()


def test_update_debt__with_current_debt_less_than_new_debt_and_total_idle_lower_than_minimum_total_idle(
    gov, asset, vault, strategy
):
    """
    Current debt is greater than new debt. Vault has a total idle value lower/equal to minimum total idle value. It cannot provide more
    assets to the strategy as there are no funds, we are therefore reverting.
    """

    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance // 2

    minimum_total_idle = vault.totalIdle()
    vault.set_minimum_total_idle(minimum_total_idle, sender=gov)
    assert vault.minimum_total_idle() == vault.totalIdle()

    # increase debt in strategy
    vault.update_max_debt_for_strategy(strategy.address, new_debt, sender=gov)

    tx = vault.update_debt(strategy.address, new_debt, sender=gov)

    assert tx.return_value == 0


def test_update_debt__with_current_debt_less_than_new_debt_and_minimum_total_idle_reducing_new_debt(
    gov, asset, vault, strategy
):
    """
    Current debt is lower than new debt. Value of minimum total idle reduces the amount of assets that the vault can provide.
    """

    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    current_debt = vault.strategies(strategy.address).current_debt

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # we ensure a small amount of liquidity remains in the vault
    minimum_total_idle = vault_balance - 1
    vault.set_minimum_total_idle(minimum_total_idle, sender=gov)
    assert vault.minimum_total_idle() == vault_balance - 1

    # vault can give as much as it reaches minimum_total_idle
    expected_new_differnce = initial_idle - minimum_total_idle
    expected_new_debt = current_debt + expected_new_differnce

    # increase debt in strategy
    vault.update_max_debt_for_strategy(strategy.address, new_debt, sender=gov)

    tx = vault.update_debt(strategy.address, new_debt, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == expected_new_debt

    assert vault.strategies(strategy.address).current_debt == expected_new_debt
    assert asset.balanceOf(strategy) == expected_new_debt
    assert asset.balanceOf(vault) == vault_balance - expected_new_differnce
    assert vault.totalIdle() == initial_idle - expected_new_differnce
    assert vault.totalDebt() == initial_debt + expected_new_differnce


def test_update_debt__with_current_debt_greater_than_new_debt_and_minimum_total_idle(
    gov, asset, vault, strategy, add_debt_to_strategy
):
    """
    Current debt is greater than new debt. Vault has a minimum total idle value small that does not affect the update_debt method.
    """
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    new_debt = vault_balance // 2
    difference = current_debt - new_debt

    add_debt_to_strategy(gov, strategy, vault, current_debt)

    # we compute vault values again, as they have changed
    vault_balance = asset.balanceOf(vault)
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # small minimum total idle value not to interfeer with update_debt method
    minimum_total_idle = 1
    vault.set_minimum_total_idle(minimum_total_idle, sender=gov)

    assert vault.minimum_total_idle() == 1

    # reduce debt in strategy
    vault.update_max_debt_for_strategy(strategy.address, new_debt, sender=gov)

    tx = vault.update_debt(strategy.address, new_debt, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    assert vault.strategies(strategy.address).current_debt == new_debt
    assert asset.balanceOf(strategy) == new_debt
    assert asset.balanceOf(vault) == vault_balance + difference
    assert vault.totalIdle() == initial_idle + difference
    assert vault.totalDebt() == initial_debt - difference


def test_update_debt__with_current_debt_greater_than_new_debt_and_total_idle_less_than_minimum_total_idle(
    gov, asset, vault, strategy, add_debt_to_strategy
):
    """
    Current debt is greater than new debt. Vault has a total idle value lower than its minimum total idle value.
    .update_debt will reduce the new debt value to increase the amount of assets that its getting from the strategy and ensure that
    total idle value is greater than minimum total idle.
    """
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    new_debt = vault_balance // 3

    add_debt_to_strategy(gov, strategy, vault, current_debt)

    # we compute vault values again, as they have changed
    vault_balance = asset.balanceOf(vault)
    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # we set minimum total idle to a value greater than debt difference
    minimum_total_idle = current_debt - new_debt + 1
    vault.set_minimum_total_idle(minimum_total_idle, sender=gov)
    assert vault.minimum_total_idle() == current_debt - new_debt + 1

    # we compute expected changes in debt due to minimum total idle need
    expected_new_difference = minimum_total_idle - initial_idle
    expected_new_debt = current_debt - expected_new_difference

    # reduce debt in strategy
    vault.update_max_debt_for_strategy(strategy.address, new_debt, sender=gov)

    tx = vault.update_debt(strategy.address, new_debt, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == expected_new_debt

    assert vault.strategies(strategy.address).current_debt == expected_new_debt
    assert asset.balanceOf(strategy) == expected_new_debt
    assert asset.balanceOf(vault) == vault_balance + expected_new_difference
    assert vault.totalIdle() == initial_idle + expected_new_difference
    assert vault.totalDebt() == initial_debt - expected_new_difference


def test_update_debt__with_faulty_strategy_that_deposits_less_than_requested(
    gov, asset, vault, faulty_strategy, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    expected_debt = current_debt // 2
    difference = current_debt - expected_debt  # maximum we can withdraw

    add_debt_to_strategy(gov, faulty_strategy, vault, current_debt)

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # check the strategy only took half and vault recorded it correctly
    assert initial_idle == expected_debt
    assert initial_debt == expected_debt
    assert vault.strategies(faulty_strategy.address).current_debt == expected_debt
    assert asset.balanceOf(faulty_strategy) == expected_debt


def test_update_debt__with_lossy_strategy_that_withdraws_less_than_requested(
    gov, asset, vault, lossy_strategy, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)

    add_debt_to_strategy(gov, lossy_strategy, vault, vault_balance)

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()
    current_debt = vault.strategies(lossy_strategy.address).current_debt
    loss = current_debt // 10
    new_debt = 0
    difference = current_debt - loss

    lossy_strategy.setWithdrawingLoss(loss, sender=gov)

    initial_pps = vault.pricePerShare()
    tx = vault.update_debt(lossy_strategy.address, 0, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    # Should have recorded the loss
    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    # assert we got back 90% of requested and it recorded the loss.
    assert vault.pricePerShare() < initial_pps
    assert vault.strategies(lossy_strategy.address).current_debt == new_debt
    assert asset.balanceOf(lossy_strategy) == new_debt
    assert asset.balanceOf(vault) == (vault_balance - loss)
    assert vault.totalIdle() == initial_idle + difference
    assert vault.totalDebt() == new_debt


def test_update_debt__with_lossy_strategy_that_withdraws_less_than_requested__max_loss(
    gov, asset, vault, lossy_strategy, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)

    add_debt_to_strategy(gov, lossy_strategy, vault, vault_balance)

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()
    current_debt = vault.strategies(lossy_strategy.address).current_debt
    loss = current_debt // 10
    new_debt = 0
    difference = current_debt - loss

    lossy_strategy.setWithdrawingLoss(loss, sender=gov)

    initial_pps = vault.pricePerShare()

    # With 0 max loss should revert.
    with ape.reverts("too much loss"):
        vault.update_debt(lossy_strategy.address, 0, 0, sender=gov)

    # Up to the loss percent still reverts
    with ape.reverts("too much loss"):
        vault.update_debt(lossy_strategy.address, 0, 999, sender=gov)

    # Over the loss percent will succeed and account correctly.
    tx = vault.update_debt(lossy_strategy.address, 0, 1_000, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    # Should have recorded the loss
    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    # assert we got back 90% of requested and it recorded the loss.
    assert vault.pricePerShare() < initial_pps
    assert vault.strategies(lossy_strategy.address).current_debt == new_debt
    assert asset.balanceOf(lossy_strategy) == new_debt
    assert asset.balanceOf(vault) == (vault_balance - loss)
    assert vault.totalIdle() == initial_idle + difference
    assert vault.totalDebt() == new_debt


def test_update_debt__with_faulty_strategy_that_withdraws_more_than_requested__only_half_withdrawn(
    gov, asset, vault, lossy_strategy, add_debt_to_strategy, airdrop_asset
):
    vault_balance = asset.balanceOf(vault)

    add_debt_to_strategy(gov, lossy_strategy, vault, vault_balance)

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()
    current_debt = vault.strategies(lossy_strategy.address).current_debt
    extra = current_debt // 10
    target_debt = current_debt // 2
    new_debt = target_debt - extra
    difference = current_debt - new_debt

    airdrop_asset(gov, asset, lossy_strategy.yieldSource(), extra)
    lossy_strategy.setWithdrawingLoss(-extra, sender=gov)

    initial_pps = vault.pricePerShare()
    tx = vault.update_debt(lossy_strategy.address, target_debt, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    # Should have recorded the extra as idle
    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    # assert we recorded correctly
    assert vault.pricePerShare() == initial_pps
    assert vault.strategies(lossy_strategy.address).current_debt == new_debt
    assert lossy_strategy.totalAssets() == target_debt
    assert asset.balanceOf(vault) == difference
    assert vault.totalIdle() == difference
    assert vault.totalDebt() == new_debt


def test_update_debt__with_faulty_strategy_that_withdraws_more_than_requested(
    gov, asset, vault, lossy_strategy, add_debt_to_strategy, airdrop_asset
):
    vault_balance = asset.balanceOf(vault)

    add_debt_to_strategy(gov, lossy_strategy, vault, vault_balance)

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()
    current_debt = vault.strategies(lossy_strategy.address).current_debt
    extra = current_debt // 10
    new_debt = 0
    difference = current_debt

    airdrop_asset(gov, asset, lossy_strategy.yieldSource(), extra)
    lossy_strategy.setWithdrawingLoss(-extra, sender=gov)

    initial_pps = vault.pricePerShare()
    tx = vault.update_debt(lossy_strategy.address, 0, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    # Should have recorded normally
    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    assert vault.pricePerShare() == initial_pps
    assert vault.strategies(lossy_strategy.address).current_debt == new_debt
    assert lossy_strategy.totalAssets() == new_debt
    assert asset.balanceOf(vault) == (vault_balance + extra)
    assert vault.totalIdle() == vault_balance
    assert vault.totalDebt() == new_debt


def test_update_debt__with_faulty_strategy_that_deposits_less_than_requested_with_airdrop(
    gov,
    asset,
    vault,
    faulty_strategy,
    add_debt_to_strategy,
    airdrop_asset,
    fish_amount,
):
    vault_balance = asset.balanceOf(vault)
    current_debt = vault_balance
    expected_debt = current_debt // 2
    difference = current_debt - expected_debt  # maximum we can withdraw

    # airdrop some asset to the vault
    airdrop_asset(gov, asset, vault, fish_amount)

    add_debt_to_strategy(gov, faulty_strategy, vault, current_debt)

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()

    # check the strategy only took half and vault recorded it correctly
    assert initial_idle == expected_debt
    assert initial_debt == expected_debt
    assert vault.strategies(faulty_strategy.address).current_debt == expected_debt
    assert asset.balanceOf(faulty_strategy) == expected_debt


def test_update_debt__with_lossy_strategy_that_withdraws_less_than_requested_with_airdrop(
    gov,
    asset,
    vault,
    lossy_strategy,
    add_debt_to_strategy,
    airdrop_asset,
    fish_amount,
):
    vault_balance = asset.balanceOf(vault)

    add_debt_to_strategy(gov, lossy_strategy, vault, vault_balance)

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()
    current_debt = vault.strategies(lossy_strategy.address).current_debt
    loss = current_debt // 10
    new_debt = 0
    difference = current_debt - loss

    lossy_strategy.setWithdrawingLoss(loss, sender=gov)

    initial_pps = vault.pricePerShare()

    # airdrop some asset to the vault
    airdrop_asset(gov, asset, vault, fish_amount)

    tx = vault.update_debt(lossy_strategy.address, 0, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    # assert we only got back half of what was requested and the vault recorded it correctly
    assert vault.pricePerShare() < initial_pps
    assert vault.strategies(lossy_strategy.address).current_debt == new_debt
    assert asset.balanceOf(lossy_strategy) == new_debt
    assert asset.balanceOf(vault) == (vault_balance - loss + fish_amount)
    assert vault.totalIdle() == initial_idle + difference
    assert vault.totalDebt() == new_debt


def test_update_debt__with_lossy_strategy_that_withdraws_less_than_requested_with_airdrop_and_max_loss(
    gov,
    asset,
    vault,
    lossy_strategy,
    add_debt_to_strategy,
    airdrop_asset,
    fish_amount,
):
    vault_balance = asset.balanceOf(vault)

    add_debt_to_strategy(gov, lossy_strategy, vault, vault_balance)

    initial_idle = vault.totalIdle()
    initial_debt = vault.totalDebt()
    current_debt = vault.strategies(lossy_strategy.address).current_debt
    loss = current_debt // 10
    new_debt = 0
    difference = current_debt - loss

    lossy_strategy.setWithdrawingLoss(loss, sender=gov)

    initial_pps = vault.pricePerShare()

    # airdrop some asset to the vault
    airdrop_asset(gov, asset, vault, fish_amount)

    # With 0 max loss should revert.
    with ape.reverts("too much loss"):
        vault.update_debt(lossy_strategy.address, 0, 0, sender=gov)

    # Up to the loss percent still reverts
    with ape.reverts("too much loss"):
        vault.update_debt(lossy_strategy.address, 0, 999, sender=gov)

    # At the amount doesn't revert
    tx = vault.update_debt(lossy_strategy.address, 0, 1_000, sender=gov)
    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == current_debt
    assert event[0].new_debt == new_debt

    # assert we only got back half of what was requested and the vault recorded it correctly
    assert vault.pricePerShare() < initial_pps
    assert vault.strategies(lossy_strategy.address).current_debt == new_debt
    assert asset.balanceOf(lossy_strategy) == new_debt
    assert asset.balanceOf(vault) == (vault_balance - loss + fish_amount)
    assert vault.totalIdle() == initial_idle + difference
    assert vault.totalDebt() == new_debt
