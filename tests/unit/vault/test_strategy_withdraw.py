import ape
import pytest
from utils import checks
from utils.constants import DAY, ROLES


def test_withdraw__with_inactive_strategy__reverts(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount
    strategy = create_strategy(vault)
    inactive_strategy = create_strategy(vault)
    strategies = [inactive_strategy]

    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    with ape.reverts("inactive strategy"):
        vault.withdraw(
            shares,
            fish.address,
            fish.address,
            [s.address for s in strategies],
            sender=fish,
        )


def test_withdraw__with_insufficient_funds_in_strategies__reverts(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount
    strategy = create_strategy(vault)
    strategies = []  # do not pass in any strategies

    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    with ape.reverts("insufficient assets in vault"):
        vault.withdraw(
            shares,
            fish.address,
            fish.address,
            [s.address for s in strategies],
            sender=fish,
        )


def test_withdraw__with_liquid_strategy_only__withdraws(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount
    strategy = create_strategy(vault)
    strategies = [strategy]

    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    tx = vault.withdraw(
        shares, fish.address, fish.address, [s.address for s in strategies], sender=fish
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(strategy) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__with_multiple_liquid_strategies__withdraws(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    amount_per_strategy = amount // 2  # deposit half of amount per strategy
    shares = amount
    first_strategy = create_strategy(vault)
    second_strategy = create_strategy(vault)
    strategies = [first_strategy, second_strategy]

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    tx = vault.withdraw(
        shares, fish.address, fish.address, [s.address for s in strategies], sender=fish
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(first_strategy) == 0
    assert asset.balanceOf(second_strategy) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__with_locked_and_liquid_strategy__withdraws(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    create_locked_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    amount_per_strategy = amount // 2  # deposit half of amount per strategy
    amount_to_lock = amount_per_strategy // 2  # lock only half of strategy
    amount_to_withdraw = amount - amount_to_lock
    shares = amount - amount_to_lock
    liquid_strategy = create_strategy(vault)
    locked_strategy = create_locked_strategy(vault)
    strategies = [locked_strategy, liquid_strategy]

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lock half of assets in locked strategy
    locked_strategy.setLockedFunds(amount_to_lock, DAY, sender=gov)

    tx = vault.withdraw(
        shares, fish.address, fish.address, [s.address for s in strategies], sender=fish
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount_to_withdraw

    assert vault.totalAssets() == amount_to_lock
    assert vault.totalSupply() == amount_to_lock
    assert vault.total_idle() == 0
    assert vault.total_debt() == amount_to_lock
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(locked_strategy) == amount_to_lock
    assert asset.balanceOf(fish) == amount_to_withdraw


def test_withdraw__with_lossy_and_liquid_strategy__withdraws():
    # TODO: implement once withdrawing from lossy is accounted for
    pass
