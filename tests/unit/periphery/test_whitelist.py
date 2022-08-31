import ape
import pytest
from utils.constants import ZERO_ADDRESS


def test_deploy_whitelist(project, bunny):
    whitelist = bunny.deploy(project.Whitelist)
    assert whitelist.owner() == bunny


def test_add_to_whitelist(project, bunny):
    whitelist = bunny.deploy(project.Whitelist)

    random_address = "0x0000000000000000000000000000000000000001"

    assert whitelist.is_whitelisted(random_address) == False

    whitelist.add_to_whitelist(random_address, sender=bunny)
    assert whitelist.is_whitelisted(random_address) == True


def test_remove_from_whitelist(project, bunny):
    whitelist = bunny.deploy(project.Whitelist)
    random_address = "0x0000000000000000000000000000000000000001"

    whitelist.add_to_whitelist(random_address, sender=bunny)
    assert whitelist.is_whitelisted(random_address)

    whitelist.remove_from_whitelist(random_address, sender=bunny)
    assert not whitelist.is_whitelisted(random_address)


def test_add_to_whitelist__reverts(project, bunny, doggie):
    whitelist = bunny.deploy(project.Whitelist)

    random_address = "0x0000000000000000000000000000000000000001"

    assert not whitelist.is_whitelisted(random_address)

    with ape.reverts():
        whitelist.add_to_whitelist(random_address, sender=doggie)

    assert not whitelist.is_whitelisted(random_address)


def test_remove_from_whitelist_reverts(project, bunny, doggie):
    whitelist = bunny.deploy(project.Whitelist)
    random_address = "0x0000000000000000000000000000000000000001"

    whitelist.add_to_whitelist(random_address, sender=bunny)
    assert whitelist.is_whitelisted(random_address)

    with ape.reverts():
        whitelist.remove_from_whitelist(random_address, sender=doggie)

    assert whitelist.is_whitelisted(random_address)
