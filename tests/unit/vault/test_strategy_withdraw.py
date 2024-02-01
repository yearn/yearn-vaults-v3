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
    max_loss = 0

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
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
            max_loss,
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
    max_loss = 0

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    tx = vault.withdraw(
        shares,
        fish.address,
        fish.address,
        max_loss,
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
    assert event[n].assets == amount

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == amount
    assert event[0].new_debt == 0

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
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    tx = vault.withdraw(
        shares,
        fish.address,
        fish.address,
        max_loss,
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
    assert event[n].assets == amount

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == first_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0
    assert event[1].strategy == second_strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(first_strategy) == 0
    assert asset.balanceOf(second_strategy) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__locked_funds_with_locked_and_liquid_strategy__reverts(
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
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lock half of assets in locked strategy
    locked_strategy.setLockedFunds(amount_to_lock, DAY, sender=gov)

    with ape.reverts("insufficient assets in vault"):
        vault.withdraw(
            amount_to_withdraw,
            fish.address,
            fish.address,
            max_loss,
            [s.address for s in strategies],
            sender=fish,
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
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lock half of assets in locked strategy
    locked_strategy.setLockedFunds(amount_to_lock, DAY, sender=gov)

    tx = vault.withdraw(
        shares,
        fish.address,
        fish.address,
        max_loss,
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
    assert event[n].assets == amount_to_withdraw

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == locked_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == amount_per_strategy - amount_to_lock
    assert event[1].strategy == liquid_strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    assert vault.totalAssets() == amount_to_lock
    assert vault.totalSupply() == amount_to_lock
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == amount_to_lock
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(locked_strategy) == amount_to_lock
    assert asset.balanceOf(fish) == amount_to_withdraw


def test_withdraw__with_lossy_strategy__no_max_loss__reverts(
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
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    with ape.reverts("too much loss"):
        vault.withdraw(
            amount_to_withdraw,
            fish.address,
            fish.address,
            max_loss,
            [lossy_strategy.address],
            sender=fish,
        )


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
    max_loss = 5_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_redeem__with_lossy_strategy__withdraws_less_than_deposited(
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
    max_loss = 10_000
    lossy_strategy = create_lossy_strategy(vault)

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.redeem(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_withdraw__with_full_loss_strategy__withdraws_none(
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
    amount_to_lose = amount_per_strategy  # loss all of strategy
    amount_to_withdraw = amount  # withdraw full deposit
    shares = amount
    lossy_strategy = create_lossy_strategy(vault)
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_redeem__with_full_loss_strategy__withdraws_none(
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
    amount_to_lose = amount_per_strategy  # loss all of strategy
    amount_to_withdraw = amount  # withdraw full deposit
    shares = amount
    lossy_strategy = create_lossy_strategy(vault)
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.redeem(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
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
    max_loss = 2_500

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0
    assert event[1].strategy == liquid_strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_redeem__with_full_lossy_and_liquid_strategy__withdraws_less_than_deposited(
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
    amount_to_lose = amount_per_strategy  # loss all of strategy
    amount_to_withdraw = amount  # withdraw full deposit
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.redeem(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0
    assert event[1].strategy == liquid_strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
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
    max_loss = 2_500

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == liquid_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0
    assert event[1].strategy == lossy_strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_redeem__with_liquid_and_full_lossy_strategy__withdraws_less_than_deposited(
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
    amount_to_lose = amount_per_strategy  # loss all of strategy
    amount_to_withdraw = amount  # withdraw full deposit
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [liquid_strategy, lossy_strategy]
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.redeem(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == liquid_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0
    assert event[1].strategy == lossy_strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_withdraw__with_liquid_and_lossy_strategy_that_losses_while_withdrawing__no_max_loss__reverts(
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
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setWithdrawingLoss(amount_to_lose, sender=gov)

    with ape.reverts("too much loss"):
        tx = vault.withdraw(
            amount_to_withdraw,
            fish.address,
            fish.address,
            max_loss,
            [s.address for s in strategies],
            sender=fish,
        )


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
    max_loss = 2_500

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setWithdrawingLoss(amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == liquid_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0
    assert event[1].strategy == lossy_strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_redeem__half_of_assets_from_lossy_strategy_that_losses_while_withdrawing__withdraws_less_than_deposited(
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
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setWithdrawingLoss(amount_to_lose, sender=gov)

    tx = vault.redeem(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
        [s.address for s in strategies],
        sender=fish,
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert (
        event[n].shares == shares // 2
    )  # only half of the total shares should be burnt
    assert event[n].assets == amount_to_withdraw - amount_to_lose

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.totalAssets() == amount // 2
    assert vault.totalSupply() == shares // 2
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == amount - amount_to_withdraw
    assert asset.balanceOf(vault) == vault.totalIdle()
    assert asset.balanceOf(liquid_strategy) == amount_per_strategy
    assert asset.balanceOf(lossy_strategy) == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose


def test_redeem__half_of_assets_from_lossy_strategy_that_losses_while_withdrawing__custom_max_loss__reverts(
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
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setWithdrawingLoss(amount_to_lose, sender=gov)

    with ape.reverts("too much loss"):
        vault.redeem(
            amount_to_withdraw,
            fish.address,
            fish.address,
            max_loss,
            [s.address for s in strategies],
            sender=fish,
        )


def test_withdraw__from_lossy_strategy_with_unrealised_losses(
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
    amount_per_strategy = amount  # deposit all of amount to strategy
    amount_to_lose = amount_per_strategy // 2  # loss only half of strategy
    amount_to_withdraw = amount
    shares = amount
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy]
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )

    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert lossy_strategy.totalAssets() == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose
    assert vault.balanceOf(fish) == 0


def test_redeem__from_lossy_strategy_with_unrealised_losses(
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
    amount_per_strategy = amount  # deposit all of amount to strategy
    amount_to_lose = amount_per_strategy // 2  # loss only half of strategy
    shares = amount
    amount_to_redeem = shares
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy]
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )

    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.redeem(
        amount_to_redeem,
        fish.address,
        fish.address,
        max_loss,
        [s.address for s in strategies],
        sender=fish,
    )

    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == amount_to_redeem
    assert event[n].assets == amount - amount_to_lose

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert lossy_strategy.totalAssets() == 0
    assert asset.balanceOf(fish) == amount - amount_to_lose
    assert vault.balanceOf(fish) == 0


def test_withdraw__from_lossy_strategy_with_unrealised_losses_and_max_redeem(
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
    amount_per_strategy = amount // 2  # deposit all of amount to strategy
    amount_to_lose = amount_per_strategy // 4  # loss only half of strategy
    amount_to_lock = (amount_per_strategy - amount_to_lose) // 2
    amount_to_withdraw = amount * 3 // 4
    shares = amount_to_withdraw
    lossy_strategy = create_lossy_strategy(vault)
    liquid_strategy = create_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )

    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)
    lossy_strategy.setLockedFunds(amount_to_lock, sender=gov)

    with ape.reverts("too much loss"):
        vault.withdraw(
            amount_to_withdraw,
            fish.address,
            fish.address,
            sender=fish,
        )

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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
    assert event[n].assets == amount_to_withdraw - (amount_to_lose // 2)

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == amount_to_lock + (amount_to_lose // 2)

    assert event[1].strategy == strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    assert vault.totalAssets() == amount - amount_to_withdraw
    assert vault.totalSupply() == amount - amount_to_withdraw
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == amount - amount_to_withdraw
    assert asset.balanceOf(vault) == 0
    assert lossy_strategy.totalAssets() == amount_to_lock
    assert asset.balanceOf(strategy) == 0
    assert liquid_strategy.totalAssets() == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - (amount_to_lose // 2)
    assert vault.balanceOf(fish) == amount - amount_to_withdraw


def test_redeem__from_lossy_strategy_with_unrealised_losses_and_max_redeem(
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
    amount_per_strategy = amount // 2  # deposit all of amount to strategy
    amount_to_lose = amount_per_strategy // 4  # loss only quarter of strategy
    amount_to_lock = (
        amount_per_strategy - amount_to_lose
    ) // 2  # lock half of whats left
    amount_to_withdraw = amount * 3 // 4
    shares = amount_to_withdraw
    lossy_strategy = create_lossy_strategy(vault)
    liquid_strategy = create_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )

    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose and lock assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)
    lossy_strategy.setLockedFunds(amount_to_lock, sender=gov)

    with ape.reverts("too much loss"):
        vault.redeem(
            shares,
            fish.address,
            fish.address,
            0,
            [s.address for s in strategies],
            sender=fish,
        )

    tx = vault.redeem(
        shares,
        fish.address,
        fish.address,
        max_loss,
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
    assert event[n].assets == amount_to_withdraw - (amount_to_lose // 2)

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == amount_to_lock + (amount_to_lose // 2)

    assert event[1].strategy == strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    assert vault.totalAssets() == amount - amount_to_withdraw
    assert vault.totalSupply() == amount - amount_to_withdraw
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == amount - amount_to_withdraw
    assert asset.balanceOf(vault) == 0
    assert lossy_strategy.totalAssets() == amount_to_lock
    assert asset.balanceOf(strategy) == 0
    assert liquid_strategy.totalAssets() == 0
    assert asset.balanceOf(fish) == amount_to_withdraw - (amount_to_lose // 2)
    assert vault.balanceOf(fish) == amount - amount_to_withdraw


def test_withdraw__from_lossy_strategy_with_unrealised_losses_full_strategy(
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
    amount_per_strategy = amount  # deposit all of amount to strategy
    amount_to_lose = amount_per_strategy  # loss all of the strategy
    amount_to_withdraw = amount
    shares = amount
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy]
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )

    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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
    assert event[n].assets == 0

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert lossy_strategy.totalAssets() == 0
    assert asset.balanceOf(fish) == 0
    assert vault.balanceOf(fish) == 0


def test_redeem__from_lossy_strategy_with_unrealised_losses_all_of_strategy(
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
    amount_per_strategy = amount  # deposit all of amount to strategy
    amount_to_lose = amount_per_strategy  # loss all of the funds
    shares = amount
    amount_to_redeem = shares
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy]
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )

    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.redeem(
        amount_to_redeem,
        fish.address,
        fish.address,
        max_loss,
        [s.address for s in strategies],
        sender=fish,
    )

    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == amount_to_redeem
    assert event[n].assets == 0

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(lossy_strategy) == 0
    assert lossy_strategy.totalAssets() == 0
    assert asset.balanceOf(fish) == amount - amount_to_lose
    assert vault.balanceOf(fish) == 0


def test_withdraw__half_of_strategy_assets_from_lossy_strategy_with_unrealised_losses__no_max_fee__reverts(
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
    amount_to_withdraw = (
        amount // 4
    )  # withdraw a quarter deposit (half of strategy debt)
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    with ape.reverts("too much loss"):
        tx = vault.withdraw(
            amount_to_withdraw,
            fish.address,
            fish.address,
            max_loss,
            [s.address for s in strategies],
            sender=fish,
        )


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
    amount_to_withdraw = (
        amount // 4
    )  # withdraw a quarter deposit (half of strategy debt)
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]
    max_loss = 5_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=gov)

    tx = vault.withdraw(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
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

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == amount_per_strategy - amount_to_withdraw

    assert vault.totalAssets() == amount - amount_to_withdraw
    assert vault.totalSupply() == amount - amount_to_withdraw
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == amount - amount_to_withdraw
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == amount_per_strategy
    assert (
        lossy_strategy.totalAssets()
        == amount_per_strategy - amount_to_lose - amount_to_lose // 2
    )  # withdrawn from strategy
    assert (
        asset.balanceOf(fish) == amount_to_withdraw - amount_to_lose // 2
    )  # it only takes half loss
    assert vault.balanceOf(fish) == amount - amount_to_withdraw


def test_redeem__half_of_strategy_assets_from_locked_lossy_strategy_with_unrealised_losses__withdraws_less_than_deposited(
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
    amount_to_lock = amount_to_lose * 9 // 10  # Lock 90% of whats remaining
    amount_to_withdraw = (
        amount // 4
    )  # withdraw a quarter deposit (half of strategy debt)
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]
    max_loss = 10_000

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    lossy_strategy.setLoss(gov, amount_to_lose, sender=lossy_strategy)
    # Lock half the remaining funds.
    lossy_strategy.setLockedFunds(amount_to_lock, sender=gov)

    tx = vault.redeem(
        amount_to_withdraw,
        fish.address,
        fish.address,
        max_loss,
        [s.address for s in strategies],
        sender=fish,
    )

    expected_locked_out = amount_to_lose * 1 // 10
    expected_locked_loss = expected_locked_out
    expected_liquid_out = (
        amount_to_withdraw - expected_locked_out - expected_locked_loss
    )

    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) > 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares // 4
    assert event[n].assets == amount_to_withdraw - expected_locked_loss

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == lossy_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert (
        event[0].new_debt
        == amount_per_strategy - expected_locked_out - expected_locked_loss
    )
    assert event[1].strategy == liquid_strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == amount_per_strategy - expected_liquid_out

    assert vault.totalAssets() == amount - amount_to_withdraw
    assert vault.totalSupply() == amount - amount_to_withdraw
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == amount - amount_to_withdraw
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(liquid_strategy) == amount_per_strategy - expected_liquid_out
    assert (
        asset.balanceOf(lossy_strategy.yieldSource())
        == amount_per_strategy - amount_to_lose - expected_locked_out
    )  # withdrawn from strategy
    assert (
        asset.balanceOf(fish) == amount_to_withdraw - expected_locked_loss
    )  # it only takes half loss
    assert vault.balanceOf(fish) == amount - amount_to_withdraw


def test_redeem__half_of_strategy_assets_from_locked_lossy_strategy_with_unrealised_losses__custom_max_loss__reverts(
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
    amount_to_lose = amount_per_strategy // 2  # loss only half of strategy
    amount_to_lock = amount_to_lose * 9 // 10  # Lock 90% of whats remaining
    amount_to_withdraw = (
        amount // 4
    )  # withdraw a quarter deposit (half of strategy debt)
    shares = amount
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_locked_strategy(vault)
    strategies = [lossy_strategy, liquid_strategy]
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # lose half of assets in lossy strategy
    asset.transfer(gov, amount_to_lose, sender=lossy_strategy)
    # Lock half the remaining funds.
    lossy_strategy.setLockedFunds(amount_to_lock, DAY, sender=gov)

    with ape.reverts("too much loss"):
        vault.redeem(
            amount_to_withdraw,
            fish.address,
            fish.address,
            max_loss,
            [s.address for s in strategies],
            sender=fish,
        )


def test_withdraw__with_multiple_liquid_strategies_more_assets_than_debt__withdraws(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    airdrop_asset,
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
    max_loss = 0

    profit = (
        amount_per_strategy + 1
    )  # enough so that it could serve a full withdraw with the profit
    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    airdrop_asset(gov, asset, gov, fish_amount)
    asset.transfer(first_strategy, profit, sender=gov)
    first_strategy.report(sender=gov)

    tx = vault.withdraw(
        shares,
        fish.address,
        fish.address,
        max_loss,
        [s.address for s in strategies],
        sender=fish,
    )
    event = list(tx.decode_logs(vault.Withdraw))

    assert vault.totalAssets() == 0
    assert len(event) >= 1
    n = len(event) - 1
    assert event[n].sender == fish
    assert event[n].receiver == fish
    assert event[n].owner == fish
    assert event[n].shares == shares
    assert event[n].assets == amount

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 2
    assert event[0].strategy == first_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0
    assert event[1].strategy == second_strategy.address
    assert event[1].current_debt == amount_per_strategy
    assert event[1].new_debt == 0

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert first_strategy.totalAssets() == profit
    assert asset.balanceOf(first_strategy) == profit
    assert asset.balanceOf(second_strategy) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__with_custom_queue_and_use_default_queue__overrides(
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
    shares = amount // 2
    first_strategy = create_strategy(vault)
    second_strategy = create_strategy(vault)
    strategies = [first_strategy, second_strategy]
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # Set override to true
    vault.set_use_default_queue(True, sender=gov)

    # Set queue to opposite of the custom one
    vault.set_default_queue([second_strategy, first_strategy], sender=gov)

    tx = vault.withdraw(
        shares,
        fish.address,
        fish.address,
        max_loss,
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
    assert event[n].assets == shares

    event = list(tx.decode_logs(vault.DebtUpdated))

    # Should have only withdrawn from second strategy
    assert len(event) == 1
    assert event[0].strategy == second_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.strategies(first_strategy)["current_debt"] == amount_per_strategy
    assert vault.strategies(second_strategy)["current_debt"] == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(first_strategy) == amount_per_strategy
    assert asset.balanceOf(second_strategy) == 0
    assert asset.balanceOf(fish) == shares
    assert vault.balanceOf(fish) > 0


def test_redeem__with_custom_queue_and_use_default_queue__overrides(
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
    shares = amount // 2
    first_strategy = create_strategy(vault)
    second_strategy = create_strategy(vault)
    strategies = [first_strategy, second_strategy]
    max_loss = 0

    # deposit assets to vault
    user_deposit(fish, vault, asset, amount)

    # set up strategies
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    for strategy in strategies:
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, amount_per_strategy)

    # Set override to true
    vault.set_use_default_queue(True, sender=gov)

    # Set queue to opposite of the custom one
    vault.set_default_queue([second_strategy, first_strategy], sender=gov)

    tx = vault.redeem(
        shares,
        fish.address,
        fish.address,
        max_loss,
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
    assert event[n].assets == shares

    event = list(tx.decode_logs(vault.DebtUpdated))

    # Should have only withdrawn from second strategy
    assert len(event) == 1
    assert event[0].strategy == second_strategy.address
    assert event[0].current_debt == amount_per_strategy
    assert event[0].new_debt == 0

    assert vault.strategies(first_strategy)["current_debt"] == amount_per_strategy
    assert vault.strategies(second_strategy)["current_debt"] == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(first_strategy) == amount_per_strategy
    assert asset.balanceOf(second_strategy) == 0
    assert asset.balanceOf(fish) == shares
    assert vault.balanceOf(fish) > 0


def test_withdraw__with_max_loss_too_high__reverts(
    fish, fish_amount, asset, create_vault
):
    vault = create_vault(asset)
    amount = fish_amount
    max_loss = 10_001

    with ape.reverts("max loss"):
        vault.withdraw(
            amount,
            fish.address,
            fish.address,
            max_loss,
            sender=fish,
        )


def test_redeem__with_max_loss_too_high__reverts(
    fish, fish_amount, asset, create_vault
):
    vault = create_vault(asset)
    shares = fish_amount
    max_loss = 10_001

    with ape.reverts("max loss"):
        vault.redeem(
            shares,
            fish.address,
            fish.address,
            max_loss,
            sender=fish,
        )
