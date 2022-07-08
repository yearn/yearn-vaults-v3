import ape
from utils import checks
from utils.constants import MAX_INT, ROLES


def test_set_role(gov, fish, asset, create_vault):
    vault = create_vault(asset)
    vault.set_role(fish.address, ROLES.DEBT_MANAGER, sender=gov)

    with ape.reverts():
        vault.set_role(fish.address, ROLES.DEBT_MANAGER, sender=fish)

    with ape.reverts():
        vault.set_role(fish.address, 100, sender=fish)
