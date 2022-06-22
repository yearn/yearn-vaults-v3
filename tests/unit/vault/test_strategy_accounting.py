import ape
from ape import chain
from utils import actions


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
    initial_gain = strategy_params.totalGain
    initial_loss = strategy_params.totalLoss
    initial_debt = strategy_params.currentDebt
    locked_profit = vault.lockedProfit()

    snapshot = chain.pending_timestamp
    tx = vault.processReport(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].totalGain == initial_gain + gain
    assert event[0].totalLoss == initial_loss
    assert event[0].currentDebt == initial_debt + gain
    assert event[0].totalFees == 0

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.totalGain == initial_gain + gain
    assert strategy_params.totalLoss == initial_loss
    assert strategy_params.currentDebt == initial_debt + gain
    assert vault.lockedProfit() == locked_profit + gain
    assert vault.strategies(strategy.address).lastReport == snapshot


def test_process_report__with_gain_and_non_zero_fees():
    # use parametrization to test multiple fee values
    # TODO: implement when FeeManager is implemented
    pass


def test_process_report__with_loss(chain, gov, asset, vault, lossy_strategy):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    loss = new_debt // 2

    # add debt to strategy and incur loss
    actions.add_debt_to_strategy(gov, lossy_strategy, vault, new_debt)
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    strategy_params = vault.strategies(lossy_strategy.address)
    initial_gain = strategy_params.totalGain
    initial_loss = strategy_params.totalLoss
    initial_debt = strategy_params.currentDebt
    locked_profit = vault.lockedProfit()

    snapshot = chain.pending_timestamp
    tx = vault.processReport(lossy_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].gain == 0
    assert event[0].loss == loss
    assert event[0].totalGain == initial_gain
    assert event[0].totalLoss == initial_loss + loss
    assert event[0].currentDebt == initial_debt - loss
    assert event[0].totalFees == 0

    strategy_params = vault.strategies(lossy_strategy.address)
    assert strategy_params.totalGain == initial_gain
    assert strategy_params.totalLoss == initial_loss + loss
    assert strategy_params.currentDebt == initial_debt - loss
    assert vault.lockedProfit() == locked_profit
    assert vault.strategies(lossy_strategy.address).lastReport == snapshot
