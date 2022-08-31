import ape
import pytest
from utils.constants import ZERO_ADDRESS


def test_deploy_whitelist(project, bunny):
    whitelist = bunny.deploy(project.Whitelist)
    assert whitelist.owner() == bunny


def test_add_to_whitelist(project, bunny):
    whitelist = bunny.deploy(project.Whitelist)

    random_address = "0xe5c8359128600615f5f1e91f97664a0862dbb391"

    assert whitelist.is_whitelisted(random_address) == False

    whitelist.add_to_whitelist(random_address, sender=bunny)
    assert whitelist.is_whitelisted(random_address) == True


def test_remove_from_whitelist(project, bunny):
    whitelist = bunny.deploy(project.Whitelist)
    random_address = "0xe5c8359128600615f5f1e91f97664a0862dbb391"

    whitelist.add_to_whitelist(random_address, sender=bunny)
    assert whitelist.is_whitelisted(random_address) == True

    whitelist.remove_from_whitelist(random_address, sender=bunny)
    assert whitelist.is_whitelisted(random_address) == False


def test_add_to_whitelist__reverts(project, bunny, doggie):
    whitelist = bunny.deploy(project.Whitelist)

    random_address = "0xe5c8359128600615f5f1e91f97664a0862dbb391"

    assert whitelist.is_whitelisted(random_address) == False

    with ape.reverts():
        whitelist.add_to_whitelist(random_address, sender=doggie)

    assert whitelist.is_whitelisted(random_address) == False


def test_remove_from_whitelist_reverts(project, bunny, doggie):
    whitelist = bunny.deploy(project.Whitelist)
    random_address = "0xe5c8359128600615f5f1e91f97664a0862dbb391"

    whitelist.add_to_whitelist(random_address, sender=bunny)
    assert whitelist.is_whitelisted(random_address) == True

    with ape.reverts():
        whitelist.remove_from_whitelist(random_address, sender=doggie)

    assert whitelist.is_whitelisted(random_address) == True
