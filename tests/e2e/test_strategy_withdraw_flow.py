import ape
from ape import chain
from utils import actions, checks
from utils.constants import DAY, MAX_INT


def test_multiple_strategy_withdraw_flow(
    chain,
    gov,
    fish,
    whale,
    fish_amount,
    whale_amount,
    bunny,
    asset,
    create_vault,
    create_strategy,
    create_locked_strategy,
):
    vault = create_vault(asset)
    vault_balance = fish_amount + whale_amount
    liquid_strategy_debt = vault_balance // 4  # deposit a quarter
    locked_strategy_debt = vault_balance // 2  # deposit half, locking half of deposit
    amount_to_lock = locked_strategy_debt // 2
    liquid_strategy = create_strategy(vault)
    locked_strategy = create_locked_strategy(vault)
    strategies = [locked_strategy, liquid_strategy]

    # deposit assets to vault
    actions.user_deposit(fish, vault, asset, fish_amount)
    actions.user_deposit(whale, vault, asset, whale_amount)

    # set up strategies
    for strategy in strategies:
        vault.addStrategy(strategy.address, sender=gov)
        strategy.setMinDebt(0, sender=gov)
        strategy.setMaxDebt(MAX_INT, sender=gov)

    vault.updateMaxDebtForStrategy(
        liquid_strategy.address, liquid_strategy_debt, sender=gov
    )
    vault.updateDebt(liquid_strategy.address, sender=gov)
    vault.updateMaxDebtForStrategy(
        locked_strategy.address, locked_strategy_debt, sender=gov
    )
    vault.updateDebt(locked_strategy.address, sender=gov)

    # lock half of assets in locked strategy
    locked_strategy.setLockedFunds(amount_to_lock, DAY, sender=gov)

    current_idle = vault_balance // 4
    current_debt = vault_balance * 3 // 4

    assert vault.totalIdle() == current_idle
    assert vault.totalDebt() == current_debt
    assert asset.balanceOf(vault) == current_idle
    assert asset.balanceOf(liquid_strategy) == liquid_strategy_debt
    assert asset.balanceOf(locked_strategy) == locked_strategy_debt

    # withdraw small amount as fish from total idle
    vault.withdraw(fish_amount // 2, fish.address, strategies, sender=fish)

    current_idle -= fish_amount // 2

    assert asset.balanceOf(fish) == fish_amount // 2
    assert vault.totalIdle() == current_idle
    assert vault.totalDebt() == current_debt
    assert asset.balanceOf(vault) == current_idle
    assert asset.balanceOf(liquid_strategy) == liquid_strategy_debt
    assert asset.balanceOf(locked_strategy) == locked_strategy_debt

    # drain remaining total idle as whale
    vault.withdraw(current_idle, whale.address, [], sender=whale)

    assert asset.balanceOf(whale) == current_idle
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == current_debt
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == liquid_strategy_debt
    assert asset.balanceOf(locked_strategy) == locked_strategy_debt

    # withdraw small amount as fish from locked_strategy to bunny
    vault.withdraw(fish_amount // 2, bunny.address, [locked_strategy], sender=fish)

    current_debt -= fish_amount // 2
    locked_strategy_debt -= fish_amount // 2

    assert asset.balanceOf(bunny) == fish_amount // 2
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == current_debt
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == liquid_strategy_debt
    assert asset.balanceOf(locked_strategy) == locked_strategy_debt

    # attempt to withdraw remaining amount from only liquid strategy but revert
    whale_balance = vault.balanceOf(whale) - amount_to_lock  # exclude locked amount
    with ape.reverts("insufficient total idle"):
        vault.withdraw(whale_balance, whale.address, [liquid_strategy], sender=whale)

    # withdraw remaining balance
    vault.withdraw(whale_balance, whale.address, strategies, sender=whale)

    assert asset.balanceOf(whale) == (whale_amount - amount_to_lock)
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == amount_to_lock
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(locked_strategy) == amount_to_lock

    # unlock locked strategy assets
    chain.pending_timestamp += DAY
    locked_strategy.freeLockedFunds(sender=gov)

    # withdraw newly unlocked funds
    strategies = [
        liquid_strategy,
        locked_strategy,
    ]  # test withdrawing from empty strategy
    vault.withdraw(amount_to_lock, whale.address, strategies, sender=whale)

    checks.check_vault_empty(vault)
    assert asset.balanceOf(whale) == whale_amount
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(locked_strategy) == 0
