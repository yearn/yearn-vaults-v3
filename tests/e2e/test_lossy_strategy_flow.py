import ape
from utils import checks
from utils.constants import MAX_INT


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
    assert event[0].total_loss == first_loss + second_loss

    assert (
        vault.strategies(strategy).current_debt
        == 2 * deposit_amount - first_loss - second_loss
    )
    assert vault.totalAssets() == 2 * deposit_amount - first_loss - second_loss

    assert 0
