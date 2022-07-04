import ape
import pytest

from utils.constants import ROLES


@pytest.fixture(autouse=True)
def set_role(vault, gov):
    vault.set_role(gov.address, ROLES.EMERGENCY_MANAGER, sender=gov)


def test_shutdown(gov, panda, vault):
    with ape.reverts():
        vault.shutdown_vault(sender=panda)
    vault.shutdown_vault(sender=gov)


def test_shutdown_cant_deposit(vault, gov, asset, mint_and_deposit_into_vault):
    vault.shutdown_vault(sender=gov)
    vault_balance_before = asset.balanceOf(vault)

    with ape.reverts():
        mint_and_deposit_into_vault(vault, gov)

    assert vault_balance_before == asset.balanceOf(vault)
    gov_balance_before = asset.balanceOf(gov)
    vault.withdraw(sender=gov)
    assert asset.balanceOf(gov) == gov_balance_before + vault_balance_before
    assert asset.balanceOf(vault) == 0
