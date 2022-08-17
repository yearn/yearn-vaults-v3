import ape
import pytest
from utils import checks
from utils.constants import MAX_INT, ZERO_ADDRESS, WEEK


def test_deposit__with_invalid_recipient__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("invalid recipient"):
        vault.deposit(amount, vault.address, sender=fish)
    with ape.reverts("invalid recipient"):
        vault.deposit(amount, ZERO_ADDRESS, sender=fish)


def test_deposit__with_zero_funds__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("cannot mint zero"):
        vault.deposit(amount, fish.address, sender=fish)


def test_deposit__with_deposit_limit_within_deposit_limit__deposit_balance(
    fish, fish_amount, asset, create_vault, user_deposit
):
    vault = create_vault(asset, deposit_limit=fish_amount)
    amount = fish_amount
    shares = amount

    tx = user_deposit(fish, vault, asset, amount)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    assert vault.total_idle() == amount
    assert vault.balanceOf(fish) == amount
    assert vault.totalSupply() == amount
    assert asset.balanceOf(fish) == 0


def test_deposit__with_deposit_limit_exceed_deposit_limit__reverts(
    fish, fish_amount, asset, create_vault
):
    amount = fish_amount
    deposit_limit = amount - 1
    vault = create_vault(asset, deposit_limit=deposit_limit)

    with ape.reverts("exceed deposit limit"):
        vault.deposit(amount, fish.address, sender=fish)


def test_deposit_all__with_deposit_limit_within_deposit_limit__deposits(
    fish, asset, create_vault
):
    balance = asset.balanceOf(fish)
    amount = balance
    shares = balance
    vault = create_vault(asset)

    asset.approve(vault.address, balance, sender=fish)
    tx = vault.deposit(MAX_INT, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    assert vault.total_idle() == balance
    assert vault.balanceOf(fish) == balance
    assert vault.totalSupply() == balance
    assert asset.balanceOf(fish) == 0


def test_deposit_all__with_deposit_limit_exceed_deposit_limit__deposit_deposit_limit(
    fish, fish_amount, asset, create_vault
):
    amount = fish_amount
    deposit_limit = amount // 2
    vault = create_vault(asset, deposit_limit=deposit_limit)

    asset.approve(vault.address, amount, sender=fish)

    with ape.reverts("exceed deposit limit"):
        vault.deposit(MAX_INT, fish.address, sender=fish)


def test_deposit__with_delegation__deposits_to_delegate(
    fish, fish_amount, bunny, asset, create_vault
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check amount is non-zero
    assert amount > 0

    # delegate deposit to bunny
    asset.approve(vault.address, amount, sender=fish)
    tx = vault.deposit(amount, bunny.address, sender=fish)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].owner == bunny
    assert event[0].shares == shares
    assert event[0].assets == amount

    # fish has no more assets
    assert asset.balanceOf(fish) == 0
    # fish has no shares
    assert vault.balanceOf(fish) == 0
    # bunny has been issued vault shares
    assert vault.balanceOf(bunny) == shares


def test_mint__with_invalid_recipient__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    shares = 0

    with ape.reverts("invalid recipient"):
        vault.mint(shares, vault.address, sender=fish)
    with ape.reverts("invalid recipient"):
        vault.mint(shares, ZERO_ADDRESS, sender=fish)


def test_mint__with_zero_funds__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    shares = 0

    with ape.reverts("cannot mint zero"):
        vault.mint(shares, fish.address, sender=fish)


def test_mint__with_deposit_limit_within_deposit_limit__deposit_balance(
    fish, fish_amount, asset, create_vault
):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount

    asset.approve(vault.address, amount, sender=fish)
    tx = vault.mint(shares, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    assert vault.total_idle() == amount
    assert vault.balanceOf(fish) == amount
    assert vault.totalSupply() == amount
    assert asset.balanceOf(fish) == 0


def test_mint__with_deposit_limit_exceed_deposit_limit__reverts(
    fish, fish_amount, asset, create_vault
):
    amount = fish_amount
    shares = amount
    deposit_limit = amount - 1
    vault = create_vault(asset, deposit_limit=deposit_limit)

    with ape.reverts("exceed deposit limit"):
        vault.mint(shares, fish.address, sender=fish)


def test_mint__with_delegation__deposits_to_delegate(
    fish, fish_amount, bunny, asset, create_vault
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check amount is non-zero
    assert amount > 0

    # delegate mint to bunny
    asset.approve(vault.address, amount, sender=fish)
    tx = vault.mint(shares, bunny.address, sender=fish)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].owner == bunny
    assert event[0].shares == shares
    assert event[0].assets == amount

    # fish has no more assets
    assert asset.balanceOf(fish) == 0
    # fish has no shares
    assert vault.balanceOf(fish) == 0
    # bunny has been issued vault shares
    assert vault.balanceOf(bunny) == shares


def test_withdraw(fish, fish_amount, asset, create_vault, user_deposit):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount

    user_deposit(fish, vault, asset, amount)

    tx = vault.withdraw(shares, fish.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__with_insufficient_shares__reverts(
    fish, fish_amount, asset, create_vault, user_deposit
):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount + 1

    user_deposit(fish, vault, asset, amount)

    with ape.reverts("insufficient shares to redeem"):
        vault.withdraw(shares, fish.address, fish.address, sender=fish)


def test_withdraw__with_no_shares__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    shares = 0

    with ape.reverts("no shares to redeem"):
        vault.withdraw(shares, fish.address, fish.address, sender=fish)


def test_withdraw__with_delegation__withdraws_to_delegate(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # withdraw to bunny
    tx = vault.withdraw(shares, bunny.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == bunny
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    # fish no longer has shares
    assert vault.balanceOf(fish) == 0
    # fish did not receive tokens
    assert asset.balanceOf(fish) == 0
    # bunny has tokens
    assert asset.balanceOf(bunny) == amount


def test_withdraw__with_delegation_and_sufficient_allowance__withdraws(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # check initial allowance is zero
    assert vault.allowance(fish, bunny) == 0

    # withdraw as bunny to fish
    vault.approve(bunny.address, amount, sender=fish)
    tx = vault.withdraw(shares, fish.address, fish.address, sender=bunny)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == bunny
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert vault.allowance(fish, bunny) == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__with_delegation_and_insufficient_allowance__reverts(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # withdraw as bunny to fish
    with ape.reverts("insufficient allowance"):
        vault.withdraw(shares, fish.address, fish.address, sender=bunny)


def test_redeem(fish, fish_amount, asset, create_vault, user_deposit):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount

    user_deposit(fish, vault, asset, amount)

    tx = vault.redeem(amount, fish.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == amount


def test_redeem__with_insufficient_shares__reverts(
    fish, fish_amount, asset, create_vault, user_deposit
):
    vault = create_vault(asset)
    amount = fish_amount
    redemption_amount = amount + 1

    user_deposit(fish, vault, asset, amount)

    with ape.reverts("insufficient shares to redeem"):
        vault.redeem(redemption_amount, fish.address, fish.address, sender=fish)


def test_redeem__with_no_shares__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("no shares to redeem"):
        vault.withdraw(amount, fish.address, fish.address, sender=fish)


def test_redeem__with_delegation__withdraws_to_delegate(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # redeem to bunny
    tx = vault.redeem(amount, bunny.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == bunny
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    # fish no longer has shares
    assert vault.balanceOf(fish) == 0
    # fish did not receive tokens
    assert asset.balanceOf(fish) == 0
    # bunny has tokens
    assert asset.balanceOf(bunny) == amount


def test_redeem__with_delegation_and_sufficient_allowance__withdraws(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # check initial allowance is zero
    assert vault.allowance(fish, bunny) == 0

    # withdraw as bunny to fish
    vault.approve(bunny.address, amount, sender=fish)
    tx = vault.redeem(amount, fish.address, fish.address, sender=bunny)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == bunny
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert vault.allowance(fish, bunny) == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == amount


def test_redeem__with_delegation_and_insufficient_allowance__reverts(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # withdraw as bunny to fish
    with ape.reverts("insufficient allowance"):
        vault.redeem(amount, fish.address, fish.address, sender=bunny)


def test_redeem__with_maximum_redemption__redeem_all(
    fish, asset, create_vault, user_deposit
):
    vault = create_vault(asset)
    balance = asset.balanceOf(fish)
    amount = balance
    shares = amount

    user_deposit(fish, vault, asset, amount)

    tx = vault.redeem(MAX_INT, fish.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == balance


@pytest.mark.parametrize("deposit_limit", [0, 10**18, MAX_INT])
def test_set_deposit_limit__with_deposit_limit(project, gov, asset, deposit_limit):
    # TODO unpermissioned set deposit limit test
    vault = gov.deploy(project.VaultV3, asset, "VaultV3", "AV", gov, WEEK)

    tx = vault.set_deposit_limit(deposit_limit, sender=gov)
    event = list(tx.decode_logs(vault.UpdateDepositLimit))

    assert event[0].deposit_limit == deposit_limit
    assert vault.deposit_limit() == deposit_limit
