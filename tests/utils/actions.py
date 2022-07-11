from ape.types import ContractLog
from utils.constants import MAX_INT


def user_deposit(user, vault, token, amount) -> ContractLog:
    initial_balance = token.balanceOf(vault)
    if token.allowance(user, vault) < amount:
        token.approve(vault.address, MAX_INT, sender=user)
    tx = vault.deposit(amount, user.address, sender=user)
    assert token.balanceOf(vault) == initial_balance + amount
    return tx


def airdrop_asset(gov, asset, target, amount):
    asset.mint(target.address, amount, sender=gov)


# used for new adding a new strategy to vault with unlimited max debt settings
def add_strategy_to_vault(user, strategy, vault):
    vault.add_strategy(strategy.address, sender=user)
    strategy.setMinDebt(0, sender=user)
    strategy.setMaxDebt(MAX_INT, sender=user)


# used to add debt to a strategy
def add_debt_to_strategy(user, strategy, vault, max_debt: int):
    vault.update_max_debt_for_strategy(strategy.address, max_debt, sender=user)
    vault.update_debt(strategy.address, sender=user)


def set_fees_for_strategy(gov, strategy, fee_manager, management_fee, performance_fee):
    fee_manager.set_management_fee(strategy.address, management_fee, sender=gov)
    fee_manager.set_performance_fee(strategy.address, performance_fee, sender=gov)
