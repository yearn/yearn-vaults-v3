import ape
from utils.constants import MAX_INT


def test_transfer__with_insufficient_funds__revert(fish, bunny, asset, create_vault):
    vault = create_vault(asset)
    amount = 1

    with ape.reverts("insufficient funds"):
        vault.transfer(bunny.address, amount, sender=fish)


def test_transfer__with_insufficient_funds__transfer(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    vault = create_vault(asset)
    amount = fish_amount

    user_deposit(fish, vault, asset, amount)

    tx = vault.transfer(bunny.address, amount, sender=fish)
    event = list(tx.decode_logs(vault.Transfer))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == bunny
    assert event[0].value == amount

    assert vault.balanceOf(fish) == 0
    assert vault.balanceOf(bunny) == amount


def test_approve__with_amount__approve(fish, fish_amount, bunny, asset, create_vault):
    vault = create_vault(asset)

    tx = vault.approve(bunny.address, MAX_INT, sender=fish)
    event = list(tx.decode_logs(vault.Approval))

    assert len(event) == 1
    assert event[0].owner == fish
    assert event[0].spender == bunny
    assert event[0].value == MAX_INT

    assert vault.allowance(fish, bunny) == MAX_INT

    # test overwrite approval
    tx = vault.approve(bunny.address, fish_amount, sender=fish)
    event = list(tx.decode_logs(vault.Approval))

    assert len(event) == 1
    assert event[0].owner == fish
    assert event[0].spender == bunny
    assert event[0].value == fish_amount

    assert vault.allowance(fish, bunny) == fish_amount


def test_transfer_from__with_approval__transfer(
    fish, fish_amount, bunny, doggie, asset, create_vault, user_deposit
):
    vault = create_vault(asset)
    amount = fish_amount

    user_deposit(fish, vault, asset, amount)

    vault.approve(bunny.address, amount, sender=fish)
    tx = vault.transferFrom(fish.address, doggie.address, amount, sender=bunny)
    approval_event = list(tx.decode_logs(vault.Approval))
    transfer_event = list(tx.decode_logs(vault.Transfer))

    assert len(approval_event) == 1
    assert approval_event[0].owner == fish
    assert approval_event[0].spender == bunny
    assert approval_event[0].value == 0

    assert len(transfer_event) == 1
    assert transfer_event[0].sender == fish
    assert transfer_event[0].receiver == doggie
    assert transfer_event[0].value == amount

    assert vault.balanceOf(fish) == 0
    assert vault.balanceOf(bunny) == 0
    assert vault.balanceOf(doggie) == amount
    assert vault.allowance(fish, bunny) == 0


def test_transfer_from__with_insufficient_allowance__reverts(
    fish, fish_amount, bunny, doggie, asset, create_vault, user_deposit
):
    vault = create_vault(asset)
    amount = fish_amount

    user_deposit(fish, vault, asset, amount)

    with ape.reverts():
        vault.transferFrom(fish.address, doggie.address, amount, sender=bunny)


def test_transfer_from__with_approval_and_insufficient_funds__reverts(
    fish, fish_amount, bunny, doggie, asset, create_vault
):
    vault = create_vault(asset)
    amount = fish_amount

    vault.approve(bunny.address, amount, sender=fish)

    with ape.reverts():
        vault.transferFrom(fish.address, doggie.address, amount, sender=bunny)
