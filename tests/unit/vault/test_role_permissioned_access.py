import ape
from utils.constants import ROLES
from utils.utils import from_units


def test_check_set_open_role_access(vault, bunny):
    with ape.reverts():
        vault.set_open_role(ROLES.STRATEGY_MANAGER, sender=bunny)


def test_set_strategy_role_open(vault, create_strategy, bunny, gov):
    new_strategy = create_strategy(vault)
    with ape.reverts():
        tx = vault.add_strategy(new_strategy, sender=bunny)
    vault.set_open_role(ROLES.STRATEGY_MANAGER, sender=gov)
    tx = vault.add_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyAdded))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address


def test_set_accounting_role_open(vault, mock_token, bunny, gov):
    mock_token.mint(vault, "1000 ether", sender=bunny)
    with ape.reverts():
        vault.sweep(mock_token, sender=bunny)
    vault.set_open_role(ROLES.ACCOUNTING_MANAGER, sender=gov)
    tx = vault.sweep(mock_token, sender=bunny)
    event = list(tx.decode_logs(vault.Sweep))
    assert len(event) == 1
    assert event[0].token == mock_token.address
    assert mock_token.balanceOf(bunny) == from_units(mock_token, 1000)


def test_set_debt_role_open(vault, bunny, gov):
    with ape.reverts():
        vault.set_minimum_total_idle(0, sender=bunny)
    vault.set_open_role(ROLES.DEBT_MANAGER, sender=gov)
    tx = vault.set_minimum_total_idle(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateMinimumTotalIdle))
    assert len(event) == 1
    assert event[0].minimum_total_idle == 0


def test_set_emergency_role_open(vault, bunny, gov):
    with ape.reverts():
        vault.shutdown_vault(sender=bunny)
    vault.set_open_role(ROLES.EMERGENCY_MANAGER, sender=gov)
    tx = vault.shutdown_vault(sender=bunny)
    event = list(tx.decode_logs(vault.Shutdown))
    assert len(event) == 1
