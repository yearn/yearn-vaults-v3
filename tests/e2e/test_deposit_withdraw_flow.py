from utils import checks
from utils.constants import MAX_INT


def test_deposit_and_withdraw(asset, fish, create_vault):
    vault = create_vault(asset)
    balance = asset.balanceOf(fish)
    half_balance = balance // 2
    asset.approve(vault.address, balance, sender=fish)
    vault.deposit(half_balance, fish.address, sender=fish)

    assert vault.totalSupply() == half_balance
    assert asset.balanceOf(vault) == half_balance
    assert vault.totalIdle() == half_balance
    assert vault.totalDebt() == 0
    # can't fetch pps?
    assert vault.pricePerShare(sender=fish) == 10 ** asset.decimals()  # 1:1 price

    # deposit again to test behavior when vault has existing shares
    vault.deposit(MAX_INT, fish.address, sender=fish)

    assert vault.totalSupply() == balance
    assert asset.balanceOf(vault) == balance
    assert vault.totalIdle() == balance
    assert vault.totalDebt() == 0
    assert vault.pricePerShare(sender=fish) == 10 ** asset.decimals()  # 1:1 price

    strategies = []
    vault.withdraw(half_balance, fish.address, strategies, sender=fish)

    assert vault.totalSupply() == half_balance
    assert asset.balanceOf(vault) == half_balance
    assert vault.totalIdle() == half_balance
    assert vault.totalDebt() == 0
    assert vault.pricePerShare(sender=fish) == 10 ** asset.decimals()  # 1:1 price

    vault.withdraw(half_balance, fish.address, strategies, sender=fish)

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert vault.pricePerShare(sender=fish) == 10 ** asset.decimals()  # 1:1 price


def test_delegated_deposit_and_withdraw(
    asset, create_vault, fish, bunny, doggie, panda, woofy
):
    vault = create_vault(asset)
    balance = asset.balanceOf(fish)
    strategies = []

    # make sure we have some assets to play with
    assert balance > 0

    # 1. Deposit from fish and send shares to bunny
    asset.approve(vault.address, asset.balanceOf(fish), sender=fish)
    vault.deposit(asset.balanceOf(fish), bunny.address, sender=fish)

    # fish no longer has any assets
    assert asset.balanceOf(fish) == 0
    # fish does not have any vault shares
    assert vault.balanceOf(fish) == 0
    # bunny has been issued the vault shares
    assert vault.balanceOf(bunny) == balance

    # 2. Withdraw from bunny to doggie
    vault.withdraw(vault.balanceOf(bunny), doggie.address, strategies, sender=bunny)

    # bunny no longer has any shares
    assert vault.balanceOf(bunny) == 0
    # bunny did not receive any assets
    assert asset.balanceOf(bunny) == 0
    # doggie has the assets
    assert asset.balanceOf(doggie) == balance

    # 3. Deposit from doggie and send shares to panda
    asset.approve(vault.address, asset.balanceOf(doggie), sender=doggie)
    vault.deposit(asset.balanceOf(doggie), panda.address, sender=doggie)

    # doggie no longer has any assets
    assert asset.balanceOf(doggie) == 0
    # doggie does not have any vault shares
    assert vault.balanceOf(doggie) == 0
    # panda has been issued the vault shares
    assert vault.balanceOf(panda) == balance

    # 4. Withdraw from panda to woofy
    vault.withdraw(vault.balanceOf(panda), woofy.address, strategies, sender=panda)

    # panda no longer has any shares
    assert vault.balanceOf(panda) == 0
    # panda did not receive any assets
    assert asset.balanceOf(panda) == 0
    # woofy has the assets
    assert asset.balanceOf(woofy) == balance
