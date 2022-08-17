import ape
from ape import chain
from utils import checks
from utils.constants import DAY, ROLES


def test_multiple_strategy_withdraw_flow(
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
    user_deposit,
    add_debt_to_strategy,
    add_strategy_to_vault,
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
    user_deposit(fish, vault, asset, fish_amount)
    user_deposit(whale, vault, asset, whale_amount)

    # set up strategies
    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)

    add_debt_to_strategy(gov, liquid_strategy, vault, liquid_strategy_debt)
    add_debt_to_strategy(gov, locked_strategy, vault, locked_strategy_debt)

    # lock half of assets in locked strategy
    locked_strategy.setLockedFunds(amount_to_lock, DAY, sender=gov)

    current_idle = vault_balance // 4
    current_debt = vault_balance * 3 // 4

    assert vault.total_idle() == current_idle
    assert vault.total_debt() == current_debt
    assert asset.balanceOf(vault) == current_idle
    assert asset.balanceOf(liquid_strategy) == liquid_strategy_debt
    assert asset.balanceOf(locked_strategy) == locked_strategy_debt

    # withdraw small amount as fish from total idle
    vault.withdraw(
        fish_amount // 2,
        fish.address,
        fish.address,
        [s.address for s in strategies],
        sender=fish,
    )

    current_idle -= fish_amount // 2

    assert asset.balanceOf(fish) == fish_amount // 2
    assert vault.total_idle() == current_idle
    assert vault.total_debt() == current_debt
    assert asset.balanceOf(vault) == current_idle
    assert asset.balanceOf(liquid_strategy) == liquid_strategy_debt
    assert asset.balanceOf(locked_strategy) == locked_strategy_debt

    # drain remaining total idle as whale
    vault.withdraw(current_idle, whale.address, whale.address, [], sender=whale)

    assert asset.balanceOf(whale) == current_idle
    assert vault.total_idle() == 0
    assert vault.total_debt() == current_debt
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == liquid_strategy_debt
    assert asset.balanceOf(locked_strategy) == locked_strategy_debt

    # withdraw small amount as fish from locked_strategy to bunny
    vault.withdraw(
        fish_amount // 2,
        bunny.address,
        fish.address,
        [locked_strategy.address],
        sender=fish,
    )

    current_debt -= fish_amount // 2
    locked_strategy_debt -= fish_amount // 2

    assert asset.balanceOf(bunny) == fish_amount // 2
    assert vault.total_idle() == 0
    assert vault.total_debt() == current_debt
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == liquid_strategy_debt
    assert asset.balanceOf(locked_strategy) == locked_strategy_debt

    # attempt to withdraw remaining amount from only liquid strategy but revert
    whale_balance = vault.balanceOf(whale) - amount_to_lock  # exclude locked amount
    with ape.reverts("insufficient assets in vault"):
        vault.withdraw(
            whale_balance,
            whale.address,
            whale.address,
            [liquid_strategy.address],
            sender=whale,
        )

    # withdraw remaining balance
    vault.withdraw(
        whale_balance,
        whale.address,
        whale.address,
        [s.address for s in strategies],
        sender=whale,
    )

    assert asset.balanceOf(whale) == (whale_amount - amount_to_lock)
    assert vault.total_idle() == 0
    assert vault.total_debt() == amount_to_lock
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
    vault.withdraw(
        amount_to_lock,
        whale.address,
        whale.address,
        [s.address for s in strategies],
        sender=whale,
    )

    checks.check_vault_empty(vault)
    assert asset.balanceOf(whale) == whale_amount
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(locked_strategy) == 0
