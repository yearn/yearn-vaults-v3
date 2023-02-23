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
    deploy_generic_queue_manager,
):
    queue_manager = deploy_generic_queue_manager()
    vault = create_vault(asset)
    vault.set_queue_manager(queue_manager, sender=gov)
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

    queue_manager.setQueue(vault, strategies, sender=gov)

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
    deploy_generic_queue_manager,
):
    queue_manager = deploy_generic_queue_manager()
    vault = create_vault(asset)
    vault.set_queue_manager(queue_manager, sender=gov)
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

    queue_manager.setQueue(vault, strategies, sender=gov)

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
    deploy_generic_queue_manager,
):
    queue_manager = deploy_generic_queue_manager()
    vault = create_vault(asset)
    vault.set_queue_manager(queue_manager, sender=gov)
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
    queue_manager.setQueue(vault, strategies, sender=gov)

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


def test_withdraw__queue__no_override_with_inactive_strategy__reverts(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    deploy_generic_queue_manager,
):
    queue_manager = deploy_generic_queue_manager()
    vault = create_vault(asset)
    vault.set_queue_manager(queue_manager, sender=gov)
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

    # add correct strategy and should be overridden
    queue_manager.setQueue(vault, [strategy], sender=gov)

    with ape.reverts("inactive strategy"):
        vault.withdraw(
            shares,
            fish.address,
            fish.address,
            [s.address for s in strategies],
            sender=fish,
        )


def test_withdraw__queue__override_with_inactive_strategy__withdraws(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    deploy_generic_queue_manager,
):
    queue_manager = deploy_generic_queue_manager()
    vault = create_vault(asset)
    vault.set_queue_manager(queue_manager, sender=gov)
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

    # add correct strategy and override
    queue_manager.setQueue(vault, [strategy], sender=gov)
    queue_manager.setForce(vault, True, sender=gov)

    tx = vault.withdraw(
        shares, fish.address, fish.address, [s.address for s in strategies], sender=fish
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
    assert asset.balanceOf(fish) == amount


# max withdraw and maxRedeem tests


def test_max_withdraw___with_queue__with_balance_greater_than_total_idle__returns_balance(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
    deploy_generic_queue_manager,
):
    queue_manager = deploy_generic_queue_manager()
    vault = create_vault(asset)
    vault.set_queue_manager(queue_manager, sender=gov)
    assets = fish_amount
    strategy = create_strategy(vault)
    strategy_deposit = assets // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)
    queue_manager.setQueue(vault, [strategy], sender=gov)

    assert vault.maxWithdraw(fish.address) == assets


def test_max_redeem__with_queue__with_balance_greater_than_total_idle__returns_balance(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
    deploy_generic_queue_manager,
):
    queue_manager = deploy_generic_queue_manager()
    vault = create_vault(asset)
    vault.set_queue_manager(queue_manager, sender=gov)
    shares = fish_amount
    assets = shares
    strategy = create_strategy(vault)
    strategy_deposit = assets // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    assert vault.maxRedeem(fish.address) == assets
