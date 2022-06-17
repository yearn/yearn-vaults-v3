import ape
from utils import actions, checks
from utils.constants import MAX_INT, ZERO_ADDRESS


def test_deposit_with_invalid_recipient(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("invalid recipient"):
        vault.deposit(amount, vault.address, sender=fish)
    with ape.reverts("invalid recipient"):
        vault.deposit(amount, ZERO_ADDRESS, sender=fish)


def test_deposit_with_zero_funds(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("cannot deposit zero"):
        vault.deposit(amount, fish.address, sender=fish)


def test_deposit(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 10**18
    shares = amount

    balance = asset.balanceOf(fish)
    tx = actions.user_deposit(fish, vault, asset, amount)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].recipient == fish
    assert event[0].shares == shares
    assert event[0].amount == amount

    assert vault.totalIdle() == amount
    assert vault.balanceOf(fish) == amount
    assert vault.totalSupply() == amount
    assert asset.balanceOf(fish) == (balance - amount)


def test_deposit_all(fish, asset, create_vault):
    vault = create_vault(asset)
    balance = asset.balanceOf(fish)
    amount = balance
    shares = balance

    asset.approve(vault.address, balance, sender=fish)
    tx = vault.deposit(MAX_INT, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].recipient == fish
    assert event[0].shares == shares
    assert event[0].amount == amount

    assert vault.totalIdle() == balance
    assert vault.balanceOf(fish) == balance
    assert vault.totalSupply() == balance
    assert asset.balanceOf(fish) == 0


def test_withdraw(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 10**18
    shares = amount
    strategies = []

    balance = asset.balanceOf(fish)
    actions.user_deposit(fish, vault, asset, amount)

    tx = vault.withdraw(shares, fish.address, strategies, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].recipient == fish
    assert event[0].shares == shares
    assert event[0].amount == amount

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
        vault.withdraw(shares, fish.address, strategies, sender=fish)


def test_withdraw_with_no_shares(fish, asset, create_vault):
    vault = create_vault(asset)
    shares = 0
    strategies = []

    with ape.reverts("no shares to withdraw"):
        vault.withdraw(shares, fish.address, strategies, sender=fish)


def test_withdraw_all(fish, asset, create_vault):
    vault = create_vault(asset)
    balance = asset.balanceOf(fish)
    amount = balance
    shares = amount
    strategies = []

    actions.user_deposit(fish, vault, asset, amount)

    tx = vault.withdraw(MAX_INT, fish.address, strategies, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].recipient == fish
    assert event[0].shares == shares
    assert event[0].amount == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == balance


def test_delegated_deposit(fish, bunny, asset, create_vault):
    vault = create_vault(asset)
    balance = asset.balanceOf(fish)
    amount = balance
    shares = amount

    # check balance is non-zero
    assert balance > 0

    # delegate deposit to bunny
    asset.approve(vault.address, amount, sender=fish)
    tx = vault.deposit(amount, bunny.address, sender=fish)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].recipient == bunny
    assert event[0].shares == shares
    assert event[0].amount == amount

    # fish has no more assets
    assert asset.balanceOf(fish) == 0
    # fish has no shares
    assert vault.balanceOf(fish) == 0
    # bunny has been issued vault shares
    assert vault.balanceOf(bunny) == balance


def test_delegated_withdrawal(fish, bunny, asset, create_vault):
    vault = create_vault(asset)
    balance = asset.balanceOf(fish)
    amount = balance
    shares = amount
    strategies = []

    # check balance is non-zero
    assert balance > 0

    # deposit balance
    actions.user_deposit(fish, vault, asset, amount)

    # withdraw to bunny
    tx = vault.withdraw(vault.balanceOf(fish), bunny.address, strategies, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].recipient == bunny
    assert event[0].shares == shares
    assert event[0].amount == amount

    # fish no longer has shares
    assert vault.balanceOf(fish) == 0
    # fish did not receive tokens
    assert asset.balanceOf(fish) == 0
    # bunny has tokens
    assert asset.balanceOf(bunny) == balance


def test_deposit_limit():
    # TODO: deposit limit tests
    pass
