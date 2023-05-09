import ape
from utils import checks
from utils.constants import MAX_INT


def test_deposit_and_withdraw(asset, gov, fish, fish_amount, create_vault):
    vault = create_vault(asset)
    amount = fish_amount
    half_amount = fish_amount // 2
    quarter_amount = half_amount // 2
    asset.approve(vault.address, amount, sender=fish)
    vault.deposit(quarter_amount, fish.address, sender=fish)

    assert vault.totalSupply() == quarter_amount
    assert asset.balanceOf(vault) == quarter_amount
    assert vault.totalIdle() == quarter_amount
    assert vault.totalDebt() == 0
    assert vault.pricePerShare(sender=fish) == 10 ** asset.decimals()  # 1:1 price

    # set deposit limit to half_amount and max deposit to test deposit limit
    vault.set_deposit_limit(half_amount, sender=gov)

    with ape.reverts("exceed deposit limit"):
        vault.deposit(amount, fish.address, sender=fish)

    vault.deposit(quarter_amount, fish.address, sender=fish)

    assert vault.totalSupply() == half_amount
    assert asset.balanceOf(vault) == half_amount
    assert vault.totalIdle() == half_amount
    assert vault.totalDebt() == 0
    assert vault.pricePerShare(sender=fish) == 10 ** asset.decimals()  # 1:1 price

    # raise deposit limit to fish_amount and allow full deposit through to test deposit limit change
    vault.set_deposit_limit(fish_amount, sender=gov)

    # deposit again to test behavior when vault has existing shares
    vault.deposit(half_amount, fish.address, sender=fish)

    assert vault.totalSupply() == amount
    assert asset.balanceOf(vault) == amount
    assert vault.totalIdle() == amount
    assert vault.totalDebt() == 0
    assert vault.pricePerShare(sender=fish) == 10 ** asset.decimals()  # 1:1 price

    vault.withdraw(half_amount, fish.address, fish.address, sender=fish)

    assert vault.totalSupply() == half_amount
    assert asset.balanceOf(vault) == half_amount
    assert vault.totalIdle() == half_amount
    assert vault.totalDebt() == 0
    assert vault.pricePerShare(sender=fish) == 10 ** asset.decimals()  # 1:1 price

    vault.withdraw(half_amount, fish.address, fish.address, sender=fish)

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert vault.pricePerShare(sender=fish) == 10 ** asset.decimals()  # 1:1 price


def test_delegated_deposit_and_withdraw(
    asset, create_vault, fish, bunny, doggie, panda, woofy
):
    vault = create_vault(asset)
    balance = asset.balanceOf(fish)

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
    vault.withdraw(vault.balanceOf(bunny), doggie.address, bunny.address, sender=bunny)

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
    vault.withdraw(vault.balanceOf(panda), woofy.address, panda.address, sender=panda)

    # panda no longer has any shares
    assert vault.balanceOf(panda) == 0
    # panda did not receive any assets
    assert asset.balanceOf(panda) == 0
    # woofy has the assets
    assert asset.balanceOf(woofy) == balance
