import ape
import pytest
from ape import chain
from utils import actions
from utils.constants import YEAR


@pytest.fixture(autouse=True)
def seed_vault_with_funds(mint_and_deposit_into_vault, vault, gov):
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)


def test_process_report__with_inactive_strategy__reverts(gov, vault, create_strategy):
    strategy = create_strategy(vault)

    with ape.reverts("inactive strategy"):
        vault.processReport(strategy.address, sender=gov)


def test_process_report__with_total_assets_equal_current_debt__reverts(
    gov, asset, vault, strategy
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance

    actions.add_debt_to_strategy(gov, strategy, vault, new_debt)

    with ape.reverts("nothing to report"):
        vault.processReport(strategy.address, sender=gov)


def test_process_report__with_unhealthy_strategy__reverts():
    # TODO: implement when health check is implemented
    pass


def test_process_report__with_gain_and_zero_fees(chain, gov, asset, vault, strategy):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2

    # add debt to strategy
    actions.add_debt_to_strategy(gov, strategy, vault, new_debt)
    actions.airdrop_asset(gov, asset, strategy, gain)

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.currentDebt
    locked_profit = vault.lockedProfit()

    snapshot = chain.pending_timestamp
    tx = vault.processReport(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].totalGain == gain
    assert event[0].totalLoss == 0
    assert event[0].currentDebt == initial_debt + gain
    assert event[0].totalFees == 0

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.totalGain == gain
    assert strategy_params.totalLoss == 0
    assert strategy_params.currentDebt == initial_debt + gain
    assert vault.lockedProfit() == locked_profit + gain
    assert vault.strategies(strategy.address).lastReport == pytest.approx(
        snapshot, abs=1
    )


def test_process_report__with_gain_and_zero_management_fees(
    chain, gov, asset, vault, strategy, fee_manager
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2
    management_fee = 0
    performance_fee = 5000
    total_fee = gain // 2

    # add debt to strategy
    actions.add_debt_to_strategy(gov, strategy, vault, new_debt)
    # airdrop gain to strategy
    actions.airdrop_asset(gov, asset, strategy, gain)
    # set up fee manager
    actions.set_fees_for_strategy(
        gov, strategy, fee_manager, management_fee, performance_fee
    )

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.currentDebt
    locked_profit = vault.lockedProfit()

    snapshot = chain.pending_timestamp
    tx = vault.processReport(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].totalGain == gain
    assert event[0].totalLoss == 0
    assert event[0].currentDebt == initial_debt + gain
    assert event[0].totalFees == total_fee

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.totalGain == gain
    assert strategy_params.totalLoss == 0
    assert strategy_params.currentDebt == initial_debt + gain
    assert vault.lockedProfit() == locked_profit + gain - total_fee
    assert vault.strategies(strategy.address).lastReport == pytest.approx(
        snapshot, abs=1
    )
    assert vault.balanceOf(fee_manager) == total_fee


def test_process_report__with_gain_and_zero_performance_fees(
    chain, gov, asset, vault, strategy, fee_manager
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2
    management_fee = 1000
    performance_fee = 0
    total_fee = vault_balance // 10  # 10% mgmt fee over all assets, over a year

    # add debt to strategy
    actions.add_debt_to_strategy(gov, strategy, vault, new_debt)
    # airdrop gain to strategy
    actions.airdrop_asset(gov, asset, strategy, gain)
    # set up fee manager
    actions.set_fees_for_strategy(
        gov, strategy, fee_manager, management_fee, performance_fee
    )

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.currentDebt
    locked_profit = vault.lockedProfit()

    chain.pending_timestamp += YEAR
    snapshot = chain.pending_timestamp
    tx = vault.processReport(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].totalGain == gain
    assert event[0].totalLoss == 0
    assert event[0].currentDebt == initial_debt + gain
    assert event[0].totalFees == pytest.approx(total_fee, rel=1e-4)

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.totalGain == gain
    assert strategy_params.totalLoss == 0
    assert strategy_params.currentDebt == initial_debt + gain
    assert vault.lockedProfit() == pytest.approx(
        locked_profit + gain - total_fee, rel=1e-4
    )
    assert vault.strategies(strategy.address).lastReport == pytest.approx(
        snapshot, abs=1
    )
    assert vault.balanceOf(fee_manager) == pytest.approx(total_fee, rel=1e-4)


def test_process_report__with_gain_and_both_fees(
    chain, gov, asset, vault, strategy, fee_manager
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2
    management_fee = 2500
    performance_fee = 2500
    total_fee = gain // 4

    # add debt to strategy
    actions.add_debt_to_strategy(gov, strategy, vault, new_debt)
    # airdrop gain to strategy
    actions.airdrop_asset(gov, asset, strategy, gain)
    # set up fee manager
    actions.set_fees_for_strategy(
        gov, strategy, fee_manager, management_fee, performance_fee
    )

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.currentDebt
    locked_profit = vault.lockedProfit()

    snapshot = chain.pending_timestamp
    tx = vault.processReport(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].totalGain == gain
    assert event[0].totalLoss == 0
    assert event[0].currentDebt == initial_debt + gain
    assert event[0].totalFees == pytest.approx(total_fee, rel=1e-4)

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.totalGain == gain
    assert strategy_params.totalLoss == 0
    assert strategy_params.currentDebt == initial_debt + gain
    assert vault.lockedProfit() == pytest.approx(
        locked_profit + gain - total_fee, rel=1e-4
    )
    assert vault.strategies(strategy.address).lastReport == pytest.approx(
        snapshot, abs=1
    )
    assert vault.balanceOf(fee_manager) == pytest.approx(total_fee, rel=1e-4)


def test_process_report__with_fees_exceeding_fee_cap(
    chain, gov, asset, vault, strategy, fee_manager
):
    # test that fees are capped to 75% of gains
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2
    management_fee = 5000
    performance_fee = 5000
    max_fee = gain * 3 // 4  # max fee set at 3/4

    # add debt to strategy
    actions.add_debt_to_strategy(gov, strategy, vault, new_debt)
    # airdrop gain to strategy
    actions.airdrop_asset(gov, asset, strategy, gain)
    # set up fee manager
    actions.set_fees_for_strategy(
        gov, strategy, fee_manager, management_fee, performance_fee
    )

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.currentDebt
    locked_profit = vault.lockedProfit()

    chain.pending_timestamp += YEAR  # need time to pass to accrue more fees
    snapshot = chain.pending_timestamp
    tx = vault.processReport(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].totalGain == gain
    assert event[0].totalLoss == 0
    assert event[0].currentDebt == initial_debt + gain
    assert event[0].totalFees == max_fee

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.totalGain == gain
    assert strategy_params.totalLoss == 0
    assert strategy_params.currentDebt == initial_debt + gain
    assert vault.lockedProfit() == locked_profit + gain - max_fee
    assert vault.strategies(strategy.address).lastReport == pytest.approx(
        snapshot, abs=1
    )
    assert vault.balanceOf(fee_manager) == max_fee


def test_process_report__with_loss(chain, gov, asset, vault, lossy_strategy):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    loss = new_debt // 2

    # add debt to strategy and incur loss
    actions.add_debt_to_strategy(gov, lossy_strategy, vault, new_debt)
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    strategy_params = vault.strategies(lossy_strategy.address)
    initial_debt = strategy_params.currentDebt
    locked_profit = vault.lockedProfit()

    snapshot = chain.pending_timestamp
    tx = vault.processReport(lossy_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].gain == 0
    assert event[0].loss == loss
    assert event[0].totalGain == 0
    assert event[0].totalLoss == loss
    assert event[0].currentDebt == initial_debt - loss
    assert event[0].totalFees == 0

    strategy_params = vault.strategies(lossy_strategy.address)
    assert strategy_params.totalGain == 0
    assert strategy_params.totalLoss == loss
    assert strategy_params.currentDebt == initial_debt - loss
    assert vault.lockedProfit() == locked_profit
    assert vault.strategies(lossy_strategy.address).lastReport == pytest.approx(
        snapshot, abs=1
    )


def test_set_fee_manager__with_fee_manager(gov, vault, fee_manager):
    tx = vault.setFeeManager(fee_manager.address, sender=gov)
    event = list(tx.decode_logs(vault.UpdateFeeManager))

    assert len(event) == 1
    assert event[0].feeManager == fee_manager.address

    assert vault.feeManager() == fee_manager.address
