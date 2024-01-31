import ape
import pytest
from web3 import Web3
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

    with ape.reverts("inactive strategy"):
        vault.withdraw(
            shares,
            fish.address,
            fish.address,
            0,
            strategies,
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

    tx = vault.withdraw(shares, fish.address, fish.address, 0, strategies, sender=fish)
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
            0,
            [s.address for s in strategies],
            sender=fish,
        )


def test__add_strategy__adds_to_queue(create_vault, asset, gov, create_strategy):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    strategy_one = create_strategy(vault)
    vault.add_strategy(strategy_one.address, sender=gov)

    assert vault.get_default_queue() == [strategy_one.address]

    strategy_two = create_strategy(vault)
    vault.add_strategy(strategy_two.address, sender=gov)

    assert vault.get_default_queue() == [strategy_one.address, strategy_two.address]


def test__add_strategy__dont_add_to_queue(create_vault, asset, gov, create_strategy):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    strategy_one = create_strategy(vault)
    vault.add_strategy(strategy_one.address, False, sender=gov)

    assert vault.get_default_queue() == []
    assert vault.strategies(strategy_one)["activation"] != 0

    strategy_two = create_strategy(vault)
    vault.add_strategy(strategy_two.address, False, sender=gov)

    assert vault.get_default_queue() == []


def test__add_eleven_strategies__adds_ten_to_queue(
    create_vault, asset, gov, create_strategy
):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    for i in range(10):
        strategy = create_strategy(vault)
        vault.add_strategy(strategy.address, sender=gov)

        assert len(vault.get_default_queue()) == i + 1

    default_queue = vault.get_default_queue()
    assert len(default_queue) == 10

    # Make sure we can still add a strategy, but doesnt change the queue
    strategy = create_strategy(vault)
    vault.add_strategy(strategy.address, sender=gov)

    assert vault.strategies(strategy.address)["activation"] != 0

    new_queue = vault.get_default_queue()
    assert default_queue == new_queue
    assert len(new_queue) == 10

    for _strategy in new_queue:
        assert _strategy != strategy.address


def test__revoke_strategy__removes_strategy_from_queue(
    create_vault, asset, gov, create_strategy
):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    strategy_one = create_strategy(vault)
    vault.add_strategy(strategy_one.address, sender=gov)

    assert vault.get_default_queue() == [strategy_one.address]

    vault.revoke_strategy(strategy_one.address, sender=gov)

    assert vault.strategies(strategy_one.address)["activation"] == 0
    assert vault.get_default_queue() == []


def test__revoke_strategy_not_in_queue(create_vault, asset, gov, create_strategy):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    strategy_one = create_strategy(vault)
    vault.add_strategy(strategy_one.address, False, sender=gov)

    assert vault.get_default_queue() == []
    assert vault.strategies(strategy_one)["activation"] != 0

    vault.revoke_strategy(strategy_one.address, sender=gov)

    assert vault.strategies(strategy_one)["activation"] == 0
    assert vault.get_default_queue() == []


def test__revoke_strategy__mulitple_strategies__removes_strategy_from_queue(
    create_vault, asset, gov, create_strategy
):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    strategy_one = create_strategy(vault)
    vault.add_strategy(strategy_one.address, sender=gov)

    assert vault.get_default_queue() == [strategy_one.address]

    strategy_two = create_strategy(vault)
    vault.add_strategy(strategy_two.address, sender=gov)

    assert vault.get_default_queue() == [strategy_one.address, strategy_two.address]

    vault.revoke_strategy(strategy_one.address, sender=gov)

    assert vault.strategies(strategy_one.address)["activation"] == 0
    assert vault.get_default_queue() == [strategy_two.address]


def test__reomve_eleventh_strategy__doesnt_change_queue(
    create_vault, asset, gov, create_strategy
):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    for i in range(10):
        strategy = create_strategy(vault)
        vault.add_strategy(strategy.address, sender=gov)

        assert len(vault.get_default_queue()) == i + 1

    default_queue = vault.get_default_queue()
    assert len(default_queue) == 10

    # Make sure we can still add a strategy, but doesnt change the queue
    strategy = create_strategy(vault)
    vault.add_strategy(strategy.address, sender=gov)

    assert vault.strategies(strategy.address)["activation"] != 0

    vault.revoke_strategy(strategy.address, sender=gov)

    assert vault.strategies(strategy.address)["activation"] == 0

    new_queue = vault.get_default_queue()
    assert default_queue == new_queue
    assert len(new_queue) == 10


def test__set_default_queue(create_vault, asset, gov, create_strategy):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    strategy_one = create_strategy(vault)
    vault.add_strategy(strategy_one.address, sender=gov)

    strategy_two = create_strategy(vault)
    vault.add_strategy(strategy_two.address, sender=gov)

    assert vault.get_default_queue() == [strategy_one.address, strategy_two.address]

    new_queue = [strategy_two.address, strategy_one.address]

    tx = vault.set_default_queue(new_queue, sender=gov)

    event = list(tx.decode_logs(vault.UpdateDefaultQueue))

    assert len(event) == 1
    event_queue = list(event[0].new_default_queue)
    # Need to checksum each address to compare it correctly.
    for i in range(len(new_queue)):
        assert Web3.to_checksum_address(event_queue[i]) == new_queue[i]


def test__set_default_queue__inactive_strategy__reverts(
    create_vault, asset, gov, create_strategy
):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    strategy_one = create_strategy(vault)
    vault.add_strategy(strategy_one.address, sender=gov)

    # Create second strategy without adding it to the vault.
    strategy_two = create_strategy(vault)

    assert vault.get_default_queue() == [strategy_one.address]

    new_queue = [strategy_two.address, strategy_one.address]

    with ape.reverts("!inactive"):
        vault.set_default_queue(new_queue, sender=gov)


def test__set_default_queue__queue_to_long__reverts(
    create_vault, asset, gov, create_strategy
):
    vault = create_vault(asset)

    assert vault.get_default_queue() == []

    strategy_one = create_strategy(vault)
    vault.add_strategy(strategy_one.address, sender=gov)

    assert vault.get_default_queue() == [strategy_one.address]

    # Create a mock queue longer than 10.
    new_queue = [strategy_one.address for i in range(11)]

    with ape.reverts():
        vault.set_default_queue(new_queue, sender=gov)
