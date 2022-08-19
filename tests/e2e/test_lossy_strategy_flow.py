from utils.constants import MAX_INT
import ape
import pytest


def test_lossy_strategy_flow(
    asset,
    gov,
    fish,
    bunny,
    fish_amount,
    create_vault,
    create_lossy_strategy,
    strategist,
    user_deposit,
    add_debt_to_strategy,
    add_strategy_to_vault,
    airdrop_asset,
):
    vault = create_vault(asset)
    strategy = create_lossy_strategy(vault)
    add_strategy_to_vault(gov, strategy, vault)

    user_1 = fish
    user_2 = bunny
    deposit_amount = fish_amount
    first_loss = deposit_amount // 4
    second_loss = deposit_amount // 2

    user_1_initial_balance = asset.balanceOf(user_1)
    # user_1 (fish) deposit assets to vault
    user_deposit(user_1, vault, asset, deposit_amount)

    assert vault.balanceOf(user_1) == deposit_amount  # 1:1 assets:shares
    assert vault.price_per_share() / 10 ** asset.decimals() == 1.0

    add_debt_to_strategy(gov, strategy, vault, deposit_amount)

    assert vault.totalAssets() == deposit_amount
    assert vault.strategies(strategy).current_debt == deposit_amount
    assert strategy.totalAssets() == deposit_amount

    # we simulate loss on strategy
    strategy.setLoss(gov, first_loss, sender=gov)

    assert strategy.totalAssets() == deposit_amount - first_loss

    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].loss == first_loss

    assert vault.price_per_share() / 10 ** asset.decimals() == 0.75

    # user_2 (bunny) deposit assets to vault
    airdrop_asset(gov, asset, user_2, deposit_amount)
    user_2_initial_balance = asset.balanceOf(user_2)
    user_deposit(user_2, vault, asset, deposit_amount)

    assert vault.totalAssets() == 2 * deposit_amount - first_loss
    assert vault.balanceOf(user_2) > vault.balanceOf(user_1)

    assert vault.total_idle() == deposit_amount
    assert vault.total_debt() == deposit_amount - first_loss

    add_debt_to_strategy(gov, strategy, vault, vault.totalAssets())

    assert strategy.totalAssets() == 2 * deposit_amount - first_loss
    assert vault.total_idle() == 0
    assert vault.total_debt() == 2 * deposit_amount - first_loss

    strategy.setLoss(gov, second_loss, sender=gov)

    assert strategy.totalAssets() == 2 * deposit_amount - first_loss - second_loss

    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].loss == second_loss

    assert (
        vault.strategies(strategy).current_debt
        == 2 * deposit_amount - first_loss - second_loss
    )
    assert vault.totalAssets() == 2 * deposit_amount - first_loss - second_loss
    assert vault.total_idle() == 0

    # Les set a `minimum_total_idle` value
    vault.set_minimum_total_idle(3 * deposit_amount // 4, sender=gov)

    # we allowed more debt than `minimum_total_idle` allows us, to ensure `update_debt`
    # forces to comply with `minimum_total_idle`
    add_debt_to_strategy(gov, strategy, vault, deposit_amount)

    assert vault.total_idle() == 3 * deposit_amount // 4
    assert (
        strategy.totalAssets()
        == 2 * deposit_amount - first_loss - second_loss - vault.total_idle()
    )
    assert vault.strategies(strategy)

    # user_1 withdraws all his shares in `vault.total_idle`. Due to the lossy strategy, his shares have less value
    # and therefore he ends up with less assets than before
    vault.redeem(MAX_INT, user_1, user_1, sender=user_1)

    assert vault.balanceOf(user_1) == 0

    # seconds loss affects user1 in relation to the shares he has within the vault
    shares_ratio = (deposit_amount - first_loss) / (2 * deposit_amount - first_loss)
    assert asset.balanceOf(user_1) < user_1_initial_balance
    assert asset.balanceOf(user_1) == pytest.approx(
        user_1_initial_balance - first_loss - second_loss * shares_ratio, 1e-5
    )

    assert vault.total_idle() < vault.minimum_total_idle()

    # we need to `update_debt` to ensure again we have minimum liquidity
    add_debt_to_strategy(gov, strategy, vault, deposit_amount // 4)

    assert strategy.totalAssets() == 0
    assert vault.strategies(strategy).current_debt == 0
    assert vault.strategies(strategy).max_debt == deposit_amount // 4

    # user_2 withdraws everything else
    with ape.reverts("insufficient shares to redeem"):
        # user_2 has now less assets, because strategy was lossy.
        vault.withdraw(deposit_amount, user_2, user_2, sender=user_2)
    vault.redeem(vault.balanceOf(user_2), user_2, user_2, sender=user_2)

    assert vault.totalAssets() == 0
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0
    assert asset.balanceOf(user_2) < user_2_initial_balance

    vault.revoke_strategy(strategy, sender=gov)
    assert vault.strategies(strategy).activation == 0
