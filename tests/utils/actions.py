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


def add_debt_to_strategy(user, strategy, vault, max_debt: int):
    vault.updateMaxDebtForStrategy(strategy.address, max_debt, sender=user)
    vault.updateDebt(strategy.address, sender=user)


def set_fees_for_strategy(gov, strategy, fee_manager, management_fee, performance_fee):
    fee_manager.set_management_fee(strategy.address, management_fee, sender=gov)
    fee_manager.set_performance_fee(strategy.address, performance_fee, sender=gov)
