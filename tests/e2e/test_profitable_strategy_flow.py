from utils.constants import MAX_BPS, MAX_INT
import pytest
import ape
from ape import chain
from utils.utils import days_to_secs


def test_profitable_strategy_flow(
    asset,
    gov,
    fish,
    bunny,
    whale,
    fish_amount,
    create_vault,
    create_lossy_strategy,
    strategist,
    user_deposit,
    add_debt_to_strategy,
    add_strategy_to_vault,
    airdrop_asset,
    set_fees_for_strategy,
    fee_manager,
):
    performance_fee = 1_000  # 10%

    user_1 = fish
    user_2 = bunny
    deposit_amount = fish_amount
    first_profit = deposit_amount // 4
    second_profit = deposit_amount // 2

    first_loss = deposit_amount // 4

    # we reset timestamp to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    # We use lossy strategy as it allows us to create losses
    strategy = create_lossy_strategy(vault)
    set_fees_for_strategy(gov, strategy, fee_manager, 0, performance_fee)
    add_strategy_to_vault(gov, strategy, vault)

    user_1_initial_balance = asset.balanceOf(user_1)
    # user_1 (fish) deposit assets to vault
    user_deposit(user_1, vault, asset, deposit_amount)

    assert vault.balanceOf(user_1) == deposit_amount  # 1:1 assets:shares
    assert vault.price_per_share() / 10 ** asset.decimals() == 1.0

    add_debt_to_strategy(gov, strategy, vault, deposit_amount)

    assert vault.totalAssets() == deposit_amount
    assert vault.strategies(strategy).current_debt == deposit_amount
    assert strategy.totalAssets() == deposit_amount

    # we simulate profit on strategy
    asset.transfer(strategy, first_profit, sender=whale)

    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].gain == first_profit

    # pps is maintained at 1:1, but assets are increased due to fees
    assert (
        vault.totalAssets() == deposit_amount + first_profit * performance_fee / MAX_BPS
    )
    assert vault.profit_distribution_rate() == int(
        first_profit * (1 - performance_fee / MAX_BPS) / days_to_secs(7) * MAX_BPS
    )
    profit_dist_rate = vault.profit_distribution_rate()
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0
    pps = vault.price_per_share()

    # let one day pass
    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    # total_assets and pps should increase due to unlocking profit. Distribution rate should not change
    assert vault.totalAssets() == pytest.approx(
        deposit_amount
        + first_profit * performance_fee / MAX_BPS
        + vault.profit_distribution_rate() / MAX_BPS * days_to_secs(1),
        1e-5,
    )
    assert vault.profit_distribution_rate() == profit_dist_rate
    assert vault.price_per_share() > pps

    user_2_initial_balance = asset.balanceOf(user_2)
    # user_2 (bunny) deposit assets to vault
    airdrop_asset(gov, asset, user_2, deposit_amount)
    user_deposit(user_2, vault, asset, deposit_amount)

    assert vault.total_idle() == deposit_amount

    strategy.totalAssets()
    add_debt_to_strategy(gov, strategy, vault, strategy.totalAssets() + deposit_amount)

    assert vault.total_idle() == 0

    # We generate second profit
    asset.transfer(strategy, second_profit, sender=whale)
    assets_before_profit = vault.totalAssets()
    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].gain == second_profit

    assert vault.totalAssets() == pytest.approx(
        assets_before_profit + second_profit * performance_fee / MAX_BPS
    )
    # Users deposited same amount of assets, but they have different shares due to pps
    assert vault.balanceOf(user_1) > vault.balanceOf(user_2)

    pps_before_loss = vault.price_per_share()
    assets_before_loss = vault.totalAssets()
    profit_dist_rate_before_loss = vault.profit_distribution_rate()
    # we create a small loss that should be damped by profit buffer
    strategy.setLoss(gov, first_loss, sender=gov)
    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].loss == first_loss

    # loss doesnt impact vault but distribution rate
    assert vault.profit_distribution_rate() < profit_dist_rate_before_loss
    assert vault.totalAssets() > assets_before_loss
    assert vault.price_per_share() > pps_before_loss

    assert vault.total_idle() == 0
    # Les set a `minimum_total_idle` value
    min_total_idle = deposit_amount // 2
    vault.set_minimum_total_idle(min_total_idle, sender=gov)

    # We update debt for minimum_total_idle to take effect
    new_debt = strategy.totalAssets() - deposit_amount // 4
    add_debt_to_strategy(gov, strategy, vault, new_debt)

    assert vault.total_idle() == min_total_idle
    # strategy has not the desired debt, as we need to have minimum_total_idle
    assert vault.strategies(strategy).current_debt != new_debt

    user_1_withdraw = vault.total_idle()
    vault.withdraw(user_1_withdraw, user_1, user_1, sender=user_1)

    assert vault.total_idle() == pytest.approx(0, abs=1)

    new_debt = strategy.totalAssets() - deposit_amount // 4
    add_debt_to_strategy(gov, strategy, vault, new_debt)

    assert vault.total_idle() == min_total_idle
    # strategy has not the desired debt, as we need to have minimum_total_idle
    assert vault.strategies(strategy).current_debt != new_debt

    # Lets let time pass to empty profit buffer
    chain.pending_timestamp = days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    with ape.reverts("nothing to report"):
        vault.process_report(strategy.address, sender=gov)

    assert vault.profit_distribution_rate() == 0
    assert vault.totalAssets() == pytest.approx(
        2 * deposit_amount
        + first_profit
        + second_profit
        - first_loss
        - user_1_withdraw,
        1e-5,
    )

    with ape.reverts("insufficient assets in vault"):
        vault.withdraw(
            vault.convertToAssets(vault.balanceOf(user_1)),
            user_1,
            user_1,
            sender=user_1,
        )

    # we need to use strategies param to take assets from strategies
    vault.withdraw(
        vault.convertToAssets(vault.balanceOf(user_1)),
        user_1,
        user_1,
        [strategy.address],
        sender=user_1,
    )

    assert vault.total_idle() == 0
    assert vault.balanceOf(user_1) == pytest.approx(0, abs=1)

    assert asset.balanceOf(user_1) > user_1_initial_balance

    vault.redeem(
        vault.balanceOf(user_2), user_2, user_2, [strategy.address], sender=user_2
    )

    assert vault.total_idle() == 0
    assert vault.balanceOf(user_2) == pytest.approx(0, abs=1)
    assert asset.balanceOf(user_2) > user_2_initial_balance

    assert vault.totalAssets() == pytest.approx(
        vault.convertToAssets(vault.balanceOf(fee_manager)), 1e-5
    )
    assert vault.totalAssets() == pytest.approx(strategy.totalAssets(), 1e-5)

    # Let's empty the strategy and revoke it
    add_debt_to_strategy(gov, strategy, vault, 0)

    assert strategy.totalAssets() == 0
    vault.revoke_strategy(strategy, sender=gov)
    assert vault.strategies(strategy).activation == 0
