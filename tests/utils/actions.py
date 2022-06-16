from ape.types import ContractLog
from utils.constants import MAX_INT


def user_deposit(user, vault, token, amount) -> ContractLog:
    if token.allowance(user, vault) < amount:
        token.approve(vault, MAX_INT, sender=user)
    tx = vault.deposit(amount, user, sender=user)
    assert token.balanceOf(vault) == amount
    return tx
