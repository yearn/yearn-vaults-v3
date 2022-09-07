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


def test_withdraw__with_liquid_strategy__withdraws(
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

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares
    assert event[n].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(first_strategy) == 0
    assert asset.balanceOf(second_strategy) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__locked_funds_with_locked_and_liquid_strategy__withdraws(
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
    amount_to_withdraw = amount
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

    with ape.reverts("insufficient assets in vault"):
        vault.withdraw(
            amount_to_withdraw, fish.address, fish.address, [s.address for s in strategies], sender=fish
        )

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

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares
    assert event[n].assets == amount_to_withdraw

    assert vault.totalAssets() == amount_to_lock
    assert vault.totalSupply() == amount_to_lock
    assert vault.total_idle() == 0
    assert vault.total_debt() == amount_to_lock
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(locked_strategy) == amount_to_lock
    assert asset.balanceOf(fish) == amount_to_withdraw


def test_withdraw__with_lossy_strategy__withdraws_less_than_deposited(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    amount_per_strategy = amount
    amount_to_lose = amount_per_strategy // 2  # loss only half of strategy
    amount_to_withdraw = amount  # withdraw full deposit
    shares = amount
    lossy_strategy = create_lossy_strategy(vault)

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        [lossy_strategy.address],
        sender=fish,
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares
    assert event[n].assets == amount_to_withdraw - amount_to_lose

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.total_idle() == 0
    assert vault.total_debt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_withdraw__with_lossy_and_liquid_strategy__withdraws_less_than_deposited(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    amount_per_strategy = amount // 2  # deposit half of amount per strategy
    amount_to_lose = amount_per_strategy // 2  # loss only half of strategy
    amount_to_withdraw = amount  # withdraw full deposit
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        [s.address for s in strategies],
        sender=fish,
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares
    assert event[n].assets == amount_to_withdraw - amount_to_lose

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.total_idle() == 0
    assert vault.total_debt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_withdraw__with_liquid_and_lossy_strategy__withdraws_less_than_deposited(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    amount_per_strategy = amount // 2  # deposit half of amount per strategy
    amount_to_lose = amount_per_strategy // 2  # loss only half of strategy
    amount_to_withdraw = amount  # withdraw full deposit
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [liquid_strategy, lossy_strategy]

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        [s.address for s in strategies],
        sender=fish,
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares
    assert event[n].assets == amount_to_withdraw - amount_to_lose

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.total_idle() == 0
    assert vault.total_debt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_withdraw__with_liquid_and_lossy_strategy_that_losses_while_withdrawing__withdraws_less_than_deposited(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    amount_per_strategy = amount // 2  # deposit half of amount per strategy
    amount_to_lose = amount_per_strategy // 2  # loss only half of strategy
    amount_to_withdraw = amount  # withdraw full deposit
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [liquid_strategy, lossy_strategy]

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setWithdrawingLoss(amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        [s.address for s in strategies],
        sender=fish,
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares
    assert event[n].assets == amount_to_withdraw - amount_to_lose

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.total_idle() == 0
    assert vault.total_debt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_withdraw__half_of_assets_from_lossy_strategy_that_losses_while_withdrawing__withdraws_less_than_deposited(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    amount_per_strategy = amount // 2  # deposit half of amount per strategy
    amount_to_lose = amount_per_strategy // 4  # loss only quarter of strategy
    amount_to_withdraw = amount // 2  # withdraw half deposit
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setWithdrawingLoss(amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        [s.address for s in strategies],
        sender=fish,
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares // 2 # only half of the total shares should be burnt
    assert event[n].assets == amount_to_withdraw - amount_to_lose

    assert vault.totalAssets() == amount // 2
    assert vault.totalSupply() == shares // 2
    assert vault.total_idle() == 0
    assert vault.total_debt() == amount - amount_to_withdraw
    assert asset.balanceOf(vault) == vault.total_idle()
    assert asset.balanceOf(liquid_strategy) == amount_per_strategy
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose



def test_withdraw__half_of_strategy_assets_from_lossy_strategy_with_unrealised_losses__withdraws_less_than_deposited(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    vault = create_vault(asset)
    amount = fish_amount
    amount_per_strategy = amount // 2  # deposit half of amount per strategy
    amount_to_lose = amount_per_strategy // 2  # loss only half of strategy
    amount_to_withdraw = amount // 4  # withdraw a quarter deposit (half of strategy debt)
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        [s.address for s in strategies],
        sender=fish,
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares // 4
    assert event[n].assets == amount_to_withdraw - amount_to_lose // 2

    assert vault.totalAssets() == amount - amount_to_withdraw
    assert vault.totalSupply() == amount - amount_to_withdraw
    assert vault.total_idle() == 0
    assert vault.total_debt() == amount - amount_to_withdraw
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == amount_per_strategy
    assert asset.balanceOf(lossy_strategy) == amount_per_strategy - amount_to_lose - amount_to_lose // 2 # withdrawn from strategy
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose // 2 # it only takes half loss
    assert vault.balanceOf(fish) == amount - amount_to_withdraw
