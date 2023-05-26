import ape
import pytest
from utils import checks
from utils.constants import DAY, ROLES


def test_withdraw__no_queue__with_insufficient_funds_in_vault__reverts(
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

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    vault.set_default_queue(strategies, sender=gov)

    with ape.reverts("insufficient assets in vault"):
        vault.withdraw(
            shares,
            fish.address,
            fish.address,
            sender=fish,
        )


def test_withdraw__queue__with_insufficient_funds_in_vault__withdraws(
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
    strategies = [strategy]  # do not pass in any strategies

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    vault.set_default_queue(strategies, sender=gov)

    tx = vault.withdraw(
        shares,
        fish.address,
        fish.address,
        sender=fish,
    )

    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares
    assert event[n].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(strategy) == 0


def test_withdraw__queue__with_inactive_strategy__reverts(
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

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    vault.set_default_queue(strategies, sender=gov)

    with ape.reverts("inactive strategy"):
        vault.withdraw(
            shares,
            fish.address,
            fish.address,
            sender=fish,
        )


def test_withdraw__queue__with_liquid_strategy__withdraws(
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

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    vault.set_default_queue(strategies, sender=gov)

    tx = vault.withdraw(shares, fish.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares
    assert event[n].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(strategy) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__queue__with_inactive_strategy__reverts(
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

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
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


# TODO: Add test to check romval and adding strategies works.
