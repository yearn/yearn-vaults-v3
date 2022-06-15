from utils import checks
from utils.constants import MAX_INT


def test_deposit_and_withdraw(asset, user, create_vault):
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
