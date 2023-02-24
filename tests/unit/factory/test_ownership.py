import ape
from ape import chain, project, reverts
from utils.constants import ZERO_ADDRESS


def test_gov_transfers_ownership(vault_factory, gov, strategist):
    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == ZERO_ADDRESS

    vault_factory.set_governance(strategist, sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == strategist

    vault_factory.accept_governance(sender=strategist)

    assert vault_factory.governance() == strategist
    assert vault_factory.pending_governance() == ZERO_ADDRESS


def test_gov_transfers_ownership__gov_cant_accept(vault_factory, gov, strategist):
    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == ZERO_ADDRESS

    vault_factory.set_governance(strategist, sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == strategist

    with ape.reverts("not pending governance"):
        vault_factory.accept_governance(sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == strategist


def test_random_transfers_ownership__fails(vault_factory, gov, strategist):
    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == ZERO_ADDRESS

    with ape.reverts("not governance"):
        vault_factory.set_governance(strategist, sender=strategist)

    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == ZERO_ADDRESS


def test_gov_transfers_ownership__can_change_pending(
    vault_factory, gov, bunny, strategist
):
    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == ZERO_ADDRESS

    vault_factory.set_governance(strategist, sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == strategist

    vault_factory.set_governance(bunny, sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pending_governance() == bunny

    with ape.reverts("not pending governance"):
        vault_factory.accept_governance(sender=strategist)

    vault_factory.accept_governance(sender=bunny)

    assert vault_factory.governance() == bunny
    assert vault_factory.pending_governance() == ZERO_ADDRESS
