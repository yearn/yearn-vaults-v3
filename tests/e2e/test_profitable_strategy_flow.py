from utils.constants import MAX_BPS_ACCOUNTANT, MAX_INT
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
    deploy_accountant,
):
    performance_fee = 1_000  # 10%

    user_1 = fish
    user_2 = bunny
    deposit_amount = fish_amount
    first_profit = deposit_amount // 4
    second_profit = deposit_amount // 2
    first_loss = deposit_amount // 4

    initial_timestamp = chain.pending_timestamp

    vault = create_vault(asset)
    accountant = deploy_accountant(vault)
    # We use lossy strategy as it allows us to create losses
    strategy = create_lossy_strategy(vault)
    set_fees_for_strategy(gov, strategy, accountant, 0, performance_fee)
    add_strategy_to_vault(gov, strategy, vault)

    user_1_initial_balance = asset.balanceOf(user_1)
    # user_1 (fish) deposit assets to vault
    user_deposit(user_1, vault, asset, deposit_amount)

    assert vault.balanceOf(user_1) == deposit_amount  # 1:1 assets:shares
    assert vault.pricePerShare() / 10 ** asset.decimals() == 1.0

    initial_total_assets = vault.totalAssets()
    initial_total_supply = vault.totalSupply()

    add_debt_to_strategy(gov, strategy, vault, deposit_amount)

    assert vault.totalAssets() == deposit_amount
    assert vault.strategies(strategy).current_debt == deposit_amount
    assert strategy.totalAssets() == deposit_amount

    # we simulate profit on strategy
    total_fee = first_profit * (performance_fee / MAX_BPS_ACCOUNTANT)
    asset.transfer(strategy, first_profit, sender=whale)
    strategy.report(sender=gov)

    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].gain == first_profit
    assert pytest.approx(deposit_amount + first_profit, 1e-5) == vault.totalAssets()

    assert (
        pytest.approx(vault.convertToAssets(vault.balanceOf(accountant)), 1e-5)
        == total_fee
    )

    pps = vault.pricePerShare()

    user_2_initial_balance = asset.balanceOf(user_2)
    # user_2 (bunny) deposit assets to vault
    airdrop_asset(gov, asset, user_2, deposit_amount)
    user_deposit(user_2, vault, asset, deposit_amount)

    assert vault.totalIdle() == deposit_amount

    add_debt_to_strategy(gov, strategy, vault, strategy.totalAssets() + deposit_amount)

    assert vault.totalIdle() == 0

    # We generate second profit
    asset.transfer(strategy, second_profit, sender=whale)
    strategy.report(sender=gov)
    assets_before_profit = vault.totalAssets()
    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].gain == second_profit

    assert pytest.approx(assets_before_profit + second_profit) == vault.totalAssets()
    # Users deposited same amount of assets, but they have different shares due to pps
    assert vault.balanceOf(user_1) > vault.balanceOf(user_2)

    pps_before_loss = vault.pricePerShare()
    assets_before_loss = vault.totalAssets()

    # we create a small loss that should be damped by profit buffer
    strategy.setLoss(gov, first_loss, sender=gov)
    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].loss == first_loss

    assert vault.totalAssets() < assets_before_loss
    assert vault.pricePerShare() > pps_before_loss

    assert vault.totalIdle() == 0
    # Les set a `minimum_total_idle` value
    min_total_idle = deposit_amount // 2
    vault.set_minimum_total_idle(min_total_idle, sender=gov)

    # We update debt for minimum_total_idle to take effect
    new_debt = strategy.totalAssets() - deposit_amount // 4
    add_debt_to_strategy(gov, strategy, vault, new_debt)

    assert vault.totalIdle() == min_total_idle
    # strategy has not the desired debt, as we need to have minimum_total_idle
    assert vault.strategies(strategy).current_debt != new_debt

    user_1_withdraw = vault.totalIdle()
    print(
        f"Unrealized losses 1= {vault.assess_share_of_unrealised_losses(strategy, user_1_withdraw)}"
    )
    print(f"Asset balance 1 {asset.balanceOf(vault.address)}")
    vault.withdraw(user_1_withdraw, user_1, user_1, sender=user_1)

    assert pytest.approx(0, abs=1) == vault.totalIdle()

    new_debt = strategy.totalAssets() - deposit_amount // 4
    add_debt_to_strategy(gov, strategy, vault, new_debt)

    assert vault.totalIdle() == min_total_idle
    # strategy has not the desired debt, as we need to have minimum_total_idle
    assert vault.strategies(strategy).current_debt != new_debt

    # Lets let time pass to empty profit buffer
    chain.pending_timestamp = initial_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert (
        pytest.approx(vault.totalAssets())
        == 2 * deposit_amount
        + first_profit
        + second_profit
        - first_loss
        - user_1_withdraw
    )

    vault.redeem(
        vault.balanceOf(user_1),
        user_1,
        user_1,
        0,
        [strategy.address],
        sender=user_1,
    )

    assert pytest.approx(0, abs=1) == vault.balanceOf(user_1)

    assert asset.balanceOf(user_1) > user_1_initial_balance

    vault.redeem(vault.balanceOf(user_2), user_2, user_2, 0, sender=user_2)

    assert pytest.approx(0, abs=1) == vault.balanceOf(user_2)
    assert asset.balanceOf(user_2) > user_2_initial_balance

    chain.mine(timestamp=chain.pending_timestamp + days_to_secs(14))

    assert pytest.approx(vault.totalAssets(), rel=1e-5) == vault.convertToAssets(
        vault.balanceOf(accountant)
    )
    assert pytest.approx(strategy.totalAssets(), 1e-5) == vault.totalAssets()

    # Let's empty the strategy and revoke it
    add_debt_to_strategy(gov, strategy, vault, 0)

    assert strategy.totalAssets() == 0
    assert vault.strategies(strategy).current_debt == 0
    vault.revoke_strategy(strategy, sender=gov)
    assert vault.strategies(strategy).activation == 0
