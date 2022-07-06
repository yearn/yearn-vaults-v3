import ape
from utils import actions, checks
from utils.constants import MAX_INT, ROLES


def test_setRole(gov, fish, asset, create_vault):
    vault = create_vault(asset)
    vault.setRole(fish.address, ROLES.DEBT_MANAGER, sender=gov)

    with ape.reverts():
        vault.setRole(fish.address, ROLES.DEBT_MANAGER, sender=fish)

    with ape.reverts():
        vault.setRole(fish.address, 100, sender=fish)
