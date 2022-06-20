from ape.types import ContractLog
from utils.constants import MAX_INT


def user_deposit(user, vault, token, amount) -> ContractLog:
    if token.allowance(user, vault) < amount:
        token.approve(vault.address, MAX_INT, sender=user)
    tx = vault.deposit(amount, user.address, sender=user)
    assert token.balanceOf(vault) == amount
    return tx


def airdrop_asset(gov, asset, target, amount):
    asset.mint(target.address, amount, sender=gov)
