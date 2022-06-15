import ape
from utils import actions, checks
from utils.constants import MAX_INT, ZERO_ADDRESS


def test_deposit_with_invalid_recipient(user, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("invalid recipient"):
        vault.deposit(amount, vault, sender=user)
    with ape.reverts("invalid recipient"):
        vault.deposit(amount, ZERO_ADDRESS, sender=user)


def test_deposit_with_zero_funds(user, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("cannot deposit zero"):
        vault.deposit(amount, user, sender=user)


def test_deposit(user, asset, create_vault):
    vault = create_vault(asset)
    amount = 10**18

    balance = asset.balanceOf(user)
    actions.user_deposit(user, vault, asset, amount)

    assert vault.totalIdle() == amount
    assert vault.balanceOf(user) == amount
    assert vault.totalSupply() == amount
    assert asset.balanceOf(user) == (balance - amount)


def test_deposit_all(user, asset, create_vault):
    vault = create_vault(asset)
    balance = asset.balanceOf(user)

    asset.approve(vault, balance, sender=user)
    vault.deposit(MAX_INT, user, sender=user)

    assert vault.totalIdle() == balance
    assert vault.balanceOf(user) == balance
    assert vault.totalSupply() == balance
    assert asset.balanceOf(user) == 0


def test_withdraw(user, asset, create_vault):
    vault = create_vault(asset)
    balance = asset.balanceOf(user)
    half_balance = balance // 2
    asset.approve(vault, balance, sender=user)
    vault.deposit(half_balance, user, sender=user)

    assert vault.totalSupply() == half_balance
    assert asset.balanceOf(vault) == half_balance
    assert vault.totalIdle() == half_balance
    assert vault.totalDebt() == 0
    # can't fetch pps?
    assert vault.pricePerShare(sender=user) == 10 ** asset.decimals()  # 1:1 price

    # deposit again to test behavior when vault has existing shares
    vault.deposit(MAX_INT, user, sender=user)

    assert vault.totalSupply() == balance
    assert asset.balanceOf(vault) == balance
    assert vault.totalIdle() == balance
    assert vault.totalDebt() == 0
    assert vault.pricePerShare(sender=user) == 10 ** asset.decimals()  # 1:1 price

    strategies = []
    vault.withdraw(half_balance, user, strategies, sender=user)

    assert vault.totalSupply() == half_balance
    assert asset.balanceOf(vault) == half_balance
    assert vault.totalIdle() == half_balance
    assert vault.totalDebt() == 0
    assert vault.pricePerShare(sender=user) == 10 ** asset.decimals()  # 1:1 price

    vault.withdraw(half_balance, user, strategies, sender=user)

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert vault.pricePerShare(sender=user) == 10 ** asset.decimals()  # 1:1 price


def test_withdraw_with_no_shares(user, asset, create_vault):
    vault = create_vault(asset)
    shares = 0
    strategies = []

    with ape.reverts("no shares"):
        vault.withdraw(shares, user, strategies, sender=user)


def test_withdraw_all(user, asset, create_vault):
    vault = create_vault(asset)
    strategies = []

    balance = asset.balanceOf(user)
    actions.user_deposit(user, vault, asset, balance)

    vault.withdraw(MAX_INT, user, strategies, sender=user)

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(user) == balance


def test_deposit_limit():
    # TODO: deposit limit tests
    pass
