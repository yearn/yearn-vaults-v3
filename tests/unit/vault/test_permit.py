import ape
from ape import chain
from eth_account import Account
from utils.constants import MAX_INT, ZERO_ADDRESS

AMOUNT = 10**18


def test_permit(bunny, asset, create_vault, sign_vault_permit):
    owner = Account.create()
    vault = create_vault(asset)
    deadline = chain.pending_timestamp + 3600
    signature = sign_vault_permit(
        vault, owner, str(bunny.address), allowance=AMOUNT, deadline=deadline
    )
    assert vault.allowance(owner.address, bunny) == 0

    vault.permit(
        owner.address,
        bunny.address,
        AMOUNT,
        deadline,
        signature.v,
        signature.r.to_bytes(32, byteorder="big"),
        signature.s.to_bytes(32, byteorder="big"),
        sender=bunny,
    )
    assert vault.allowance(owner.address, bunny) == AMOUNT


def test_permit__with_used_permit__reverts(
    bunny, asset, create_vault, sign_vault_permit
):
    owner = Account.create()
    vault = create_vault(asset)
    deadline = chain.pending_timestamp + 3600
    signature = sign_vault_permit(
        vault, owner, str(bunny.address), allowance=AMOUNT, deadline=deadline
    )
    vault.permit(
        owner.address,
        bunny.address,
        AMOUNT,
        deadline,
        signature.v,
        signature.r.to_bytes(32, byteorder="big"),
        signature.s.to_bytes(32, byteorder="big"),
        sender=bunny,
    )

    with ape.reverts():
        vault.permit(
            owner.address,
            bunny.address,
            AMOUNT,
            deadline,
            signature.v,
            signature.r.to_bytes(32, byteorder="big"),
            signature.s.to_bytes(32, byteorder="big"),
            sender=bunny,
        )


def test_permit__with_wrong_signature__reverts(bunny, vault, sign_vault_permit):
    owner = Account.create()
    deadline = chain.pending_timestamp + 3600
    # NOTE: Default `allowance` is unlimited, not `AMOUNT`
    signature = sign_vault_permit(vault, owner, str(bunny.address))
    assert vault.allowance(owner.address, bunny) == 0
    with ape.reverts("invalid signature"):
        # Fails because wrong `allowance` value provided
        vault.permit(
            owner.address,
            bunny.address,
            AMOUNT,
            deadline,
            signature.v,
            signature.r.to_bytes(32, byteorder="big"),
            signature.s.to_bytes(32, byteorder="big"),
            sender=bunny,
        )


def test_permit_with_expired_deadline__reverts(bunny, vault, sign_vault_permit):
    owner = Account.create()
    deadline = chain.pending_timestamp - 600
    # NOTE: Default `deadline` is 0, not a timestamp in the past
    signature = sign_vault_permit(vault, owner, str(bunny.address), allowance=AMOUNT)
    assert vault.allowance(owner.address, bunny) == 0
    with ape.reverts("permit expired"):
        # Fails because wrong `deadline` timestamp provided (it expired)
        vault.permit(
            owner.address,
            bunny.address,
            AMOUNT,
            deadline,
            signature.v,
            signature.r.to_bytes(32, byteorder="big"),
            signature.s.to_bytes(32, byteorder="big"),
            sender=bunny,
        )


def test_permit__with_bad_owner__reverts(bunny, vault, sign_vault_permit):
    owner = Account.create()
    signature = sign_vault_permit(vault, owner, str(bunny.address), allowance=AMOUNT)
    assert vault.allowance(owner.address, owner.address) == 0
    with ape.reverts("invalid owner"):
        # Fails because wrong `owner` provided
        vault.permit(
            ZERO_ADDRESS,
            bunny.address,
            AMOUNT,
            0,
            signature.v,
            signature.r.to_bytes(32, byteorder="big"),
            signature.s.to_bytes(32, byteorder="big"),
            sender=bunny,
        )
