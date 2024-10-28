import ape
import pytest
from utils.constants import ROLES, ZERO_ADDRESS


@pytest.fixture(autouse=True)
def set_role(vault, gov):
    vault.set_role(
        gov.address,
        ROLES.EMERGENCY_MANAGER
        | ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.DEPOSIT_LIMIT_MANAGER,
        sender=gov,
    )


def test_shutdown(gov, panda, vault):
    with ape.reverts():
        vault.shutdown_vault(sender=panda)
    vault.shutdown_vault(sender=gov)


def test_shutdown_gives_debt_manager_role(gov, panda, vault):
    vault.set_role(panda.address, ROLES.EMERGENCY_MANAGER, sender=gov)
    assert ROLES.DEBT_MANAGER not in ROLES(vault.roles(panda))
    tx = vault.shutdown_vault(sender=panda)
    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == panda.address
    assert event[0].role == ROLES.DEBT_MANAGER | ROLES.EMERGENCY_MANAGER
    assert ROLES.DEBT_MANAGER | ROLES.EMERGENCY_MANAGER == vault.roles(panda)


def test_shutdown__increase_deposit_limit__reverts(
    vault, gov, asset, mint_and_deposit_into_vault
):
    mint_and_deposit_into_vault(vault, gov)
    vault.shutdown_vault(sender=gov)

    assert vault.maxDeposit(gov) == 0

    vault.set_role(gov, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    assert ROLES.DEPOSIT_LIMIT_MANAGER in ROLES(vault.roles(gov))

    limit = int(1e18)

    with ape.reverts():
        vault.set_deposit_limit(limit, sender=gov)

    assert vault.maxDeposit(gov) == 0


def test_shutdown__set_deposit_limit_module__reverts(
    vault, gov, asset, mint_and_deposit_into_vault, deploy_limit_module
):
    mint_and_deposit_into_vault(vault, gov)
    vault.shutdown_vault(sender=gov)

    assert vault.maxDeposit(gov) == 0

    vault.set_role(gov, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    assert ROLES.DEPOSIT_LIMIT_MANAGER in ROLES(vault.roles(gov))

    limit_module = deploy_limit_module()

    with ape.reverts():
        vault.set_deposit_limit_module(limit_module, sender=gov)

    assert vault.maxDeposit(gov) == 0


def test_shutdown__deposit_limit_module_is_removed(
    create_vault, gov, asset, mint_and_deposit_into_vault, deploy_limit_module
):
    vault = create_vault(asset)

    mint_and_deposit_into_vault(vault, gov)

    limit_module = deploy_limit_module()
    vault.set_deposit_limit_module(limit_module, sender=gov)

    assert vault.maxDeposit(gov) > 0

    tx = vault.shutdown_vault(sender=gov)

    event = list(tx.decode_logs(vault.UpdateDepositLimitModule))

    assert len(event) == 1
    assert event[0].deposit_limit_module == ZERO_ADDRESS

    assert vault.deposit_limit_module() == ZERO_ADDRESS
    assert vault.maxDeposit(gov) == 0


def test_shutdown_cant_deposit_can_withdraw(
    vault, gov, asset, mint_and_deposit_into_vault
):
    mint_and_deposit_into_vault(vault, gov)
    vault.shutdown_vault(sender=gov)

    assert vault.maxDeposit(gov) == 0
    vault_balance_before = asset.balanceOf(vault)

    with ape.reverts():
        mint_and_deposit_into_vault(vault, gov)

    assert vault_balance_before == asset.balanceOf(vault)
    gov_balance_before = asset.balanceOf(gov)
    vault.withdraw(vault.balanceOf(gov.address), gov.address, gov.address, sender=gov)
    assert asset.balanceOf(gov) == gov_balance_before + vault_balance_before
    assert asset.balanceOf(vault) == 0


def test_strategy_return_funds(
    vault, strategy, asset, gov, mint_and_deposit_into_vault, add_debt_to_strategy
):
    mint_and_deposit_into_vault(vault, gov)
    vault_balance = asset.balanceOf(vault)
    assert vault_balance != 0
    add_debt_to_strategy(gov, strategy, vault, vault_balance)
    assert asset.balanceOf(strategy) == vault_balance
    assert asset.balanceOf(vault) == 0
    vault.shutdown_vault(sender=gov)

    assert vault.maxDeposit(gov) == 0

    vault.update_debt(strategy.address, 0, sender=gov)
    assert asset.balanceOf(strategy) == 0
    assert asset.balanceOf(vault) == vault_balance
