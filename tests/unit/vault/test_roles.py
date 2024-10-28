import ape
from utils import checks
from utils.constants import MAX_INT, ROLES, ZERO_ADDRESS


def test_set_role(gov, fish, asset, create_vault):
    vault = create_vault(asset)
    vault.set_role(fish.address, ROLES.DEBT_MANAGER, sender=gov)

    with ape.reverts():
        vault.set_role(fish.address, ROLES.DEBT_MANAGER, sender=fish)

    with ape.reverts():
        vault.set_role(fish.address, 100, sender=fish)


def test_transfers_role_manager(vault, gov, strategist):
    assert vault.role_manager() == gov
    assert vault.future_role_manager() == ZERO_ADDRESS

    tx = vault.transfer_role_manager(strategist, sender=gov)
    event = list(tx.decode_logs(vault.UpdateFutureRoleManager))
    assert len(event) == 1
    assert event[0].future_role_manager == strategist

    assert vault.role_manager() == gov
    assert vault.future_role_manager() == strategist

    tx = vault.accept_role_manager(sender=strategist)
    event = list(tx.decode_logs(vault.UpdateRoleManager))
    assert len(event) == 1
    assert event[0].role_manager == strategist

    assert vault.role_manager() == strategist
    assert vault.future_role_manager() == ZERO_ADDRESS


def test_gov_transfers_role_manager__gov_cant_accept(vault, gov, strategist):
    assert vault.role_manager() == gov
    assert vault.future_role_manager() == ZERO_ADDRESS

    tx = vault.transfer_role_manager(strategist, sender=gov)
    event = list(tx.decode_logs(vault.UpdateFutureRoleManager))
    assert len(event) == 1
    assert event[0].future_role_manager == strategist

    assert vault.role_manager() == gov
    assert vault.future_role_manager() == strategist

    with ape.reverts():
        vault.accept_role_manager(sender=gov)

    assert vault.role_manager() == gov
    assert vault.future_role_manager() == strategist


def test_random_transfers_role_manager__reverts(vault, gov, strategist):
    assert vault.role_manager() == gov
    assert vault.future_role_manager() == ZERO_ADDRESS

    with ape.reverts():
        vault.transfer_role_manager(strategist, sender=strategist)

    assert vault.role_manager() == gov
    assert vault.future_role_manager() == ZERO_ADDRESS


def test_gov_transfers_role_manager__can_change_future_manager(
    vault, gov, bunny, strategist
):
    assert vault.role_manager() == gov
    assert vault.future_role_manager() == ZERO_ADDRESS

    tx = vault.transfer_role_manager(strategist, sender=gov)
    event = list(tx.decode_logs(vault.UpdateFutureRoleManager))
    assert len(event) == 1
    assert event[0].future_role_manager == strategist

    assert vault.role_manager() == gov
    assert vault.future_role_manager() == strategist

    tx = vault.transfer_role_manager(bunny, sender=gov)
    event = list(tx.decode_logs(vault.UpdateFutureRoleManager))
    assert len(event) == 1
    assert event[0].future_role_manager == bunny

    assert vault.role_manager() == gov
    assert vault.future_role_manager() == bunny

    with ape.reverts():
        vault.accept_role_manager(sender=strategist)

    tx = vault.accept_role_manager(sender=bunny)
    event = list(tx.decode_logs(vault.UpdateRoleManager))
    assert len(event) == 1
    assert event[0].role_manager == bunny

    assert vault.role_manager() == bunny
    assert vault.future_role_manager() == ZERO_ADDRESS
