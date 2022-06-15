from utils.constants import MAX_INT


def user_deposit(user, vault, token, amount):
    if token.allowance(user, vault) < amount:
        token.approve(vault, MAX_INT, sender=user)
    vault.deposit(amount, user, sender=user)
    assert token.balanceOf(vault) == amount
