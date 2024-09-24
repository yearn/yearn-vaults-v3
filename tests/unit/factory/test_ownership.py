import ape
from ape import chain, project, reverts
from utils.constants import ZERO_ADDRESS


def test_gov_transfers_ownership(vault_factory, gov, strategist):
    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == ZERO_ADDRESS

    vault_factory.transferGovernance(strategist, sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == strategist

    vault_factory.acceptGovernance(sender=strategist)

    assert vault_factory.governance() == strategist
    assert vault_factory.pendingGovernance() == ZERO_ADDRESS


def test_gov_transfers_ownership__gov_cant_accept(vault_factory, gov, strategist):
    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == ZERO_ADDRESS

    vault_factory.transferGovernance(strategist, sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == strategist

    with ape.reverts("not pending governance"):
        vault_factory.acceptGovernance(sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == strategist


def test_random_transfers_ownership__fails(vault_factory, gov, strategist):
    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == ZERO_ADDRESS

    with ape.reverts("not governance"):
        vault_factory.transferGovernance(strategist, sender=strategist)

    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == ZERO_ADDRESS


def test_gov_transfers_ownership__can_change_pending(
    vault_factory, gov, bunny, strategist
):
    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == ZERO_ADDRESS

    vault_factory.transferGovernance(strategist, sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == strategist

    vault_factory.transferGovernance(bunny, sender=gov)

    assert vault_factory.governance() == gov
    assert vault_factory.pendingGovernance() == bunny

    with ape.reverts("not pending governance"):
        vault_factory.acceptGovernance(sender=strategist)

    vault_factory.acceptGovernance(sender=bunny)

    assert vault_factory.governance() == bunny
    assert vault_factory.pendingGovernance() == ZERO_ADDRESS
