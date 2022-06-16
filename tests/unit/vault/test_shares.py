import ape
from utils import actions, checks
from utils.constants import MAX_INT, ZERO_ADDRESS


def test_deposit_with_invalid_recipient(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("invalid recipient"):
        vault.deposit(amount, vault, sender=fish)
    with ape.reverts("invalid recipient"):
        vault.deposit(amount, ZERO_ADDRESS, sender=fish)


def test_deposit_with_zero_funds(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("cannot deposit zero"):
        vault.deposit(amount, fish, sender=fish)


def test_deposit(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 10**18

    balance = asset.balanceOf(fish)
    actions.user_deposit(fish, vault, asset, amount)

    assert vault.totalIdle() == amount
    assert vault.balanceOf(fish) == amount
    assert vault.totalSupply() == amount
    assert asset.balanceOf(fish) == (balance - amount)


def test_deposit_all(fish, asset, create_vault):
    vault = create_vault(asset)
    balance = asset.balanceOf(fish)

    asset.approve(vault, balance, sender=fish)
    vault.deposit(MAX_INT, fish, sender=fish)

    assert vault.totalIdle() == balance
    assert vault.balanceOf(fish) == balance
    assert vault.totalSupply() == balance
    assert asset.balanceOf(fish) == 0


def test_withdraw(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 10**18
    strategies = []

    balance = asset.balanceOf(fish)
    actions.user_deposit(fish, vault, asset, amount)

    vault.withdraw(amount, fish, strategies, sender=fish)
    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == balance


def test_withdraw_with_insufficient_shares(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 10**18
    strategies = []
    shares = amount + 1

    actions.user_deposit(fish, vault, asset, amount)

    with ape.reverts("insufficient shares to withdraw"):
        vault.withdraw(shares, fish, strategies, sender=fish)


def test_withdraw_with_no_shares(fish, asset, create_vault):
    vault = create_vault(asset)
    shares = 0
    strategies = []

    with ape.reverts("no shares to withdraw"):
        vault.withdraw(shares, fish, strategies, sender=fish)


def test_withdraw_all(fish, asset, create_vault):
    vault = create_vault(asset)
    strategies = []

    balance = asset.balanceOf(fish)
    actions.user_deposit(fish, vault, asset, balance)

    vault.withdraw(MAX_INT, fish, strategies, sender=fish)

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == balance


def test_deposit_limit():
    # TODO: deposit limit tests
    pass
