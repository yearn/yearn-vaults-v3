import ape
from ape import project, reverts
from utils.constants import WEEK


def test_new_vault_with_different_salt(gov, asset, bunny, fish, vault_factory):
    assert vault_factory.name() == "Vault V3 Factory test"

    tx = vault_factory.deploy_new_vault(
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        WEEK,
        sender=gov,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address

    tx = vault_factory.deploy_new_vault(
        asset.address,
        "second_vault",
        "sv",
        fish.address,
        WEEK,
        sender=gov,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "second_vault"
    assert new_vault.role_manager() == fish.address


def test_new_vault_same_name_asset_and_symbol_different_sender(
    gov, asset, bunny, vault_factory
):
    tx = vault_factory.deploy_new_vault(
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        WEEK,
        sender=gov,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address

    vault_factory.deploy_new_vault(
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        WEEK,
        sender=bunny,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address


def test_new_vault_same_sender_name_asset_and_symbol__reverts(
    gov, asset, bunny, vault_factory
):
    tx = vault_factory.deploy_new_vault(
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        WEEK,
        sender=gov,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address

    with ape.reverts():
        vault_factory.deploy_new_vault(
            asset.address,
            "first_vault",
            "fv",
            bunny.address,
            WEEK,
            sender=gov,
        )


def test__shutdown_factory(gov, asset, bunny, vault_factory):
    assert vault_factory.shutdown() == False

    tx = vault_factory.shutdown_factory(sender=gov)

    event = list(tx.decode_logs(vault_factory.FactoryShutdown))

    assert len(event) == 1

    assert vault_factory.shutdown() == True

    with ape.reverts("shutdown"):
        vault_factory.deploy_new_vault(
            asset.address,
            "first_vault",
            "fv",
            bunny.address,
            WEEK,
            sender=gov,
        )


def test__shutdown_factory__reverts(gov, asset, bunny, vault_factory):
    assert vault_factory.shutdown() == False

    with ape.reverts("not governance"):
        vault_factory.shutdown_factory(sender=bunny)


def test_reinitialize_vault__reverst(gov, asset, bunny, vault_factory):
    # Can't initialize the original
    original = project.VaultV3.at(vault_factory.vault_original())

    with ape.reverts("initialized"):
        original.initialize(
            asset.address,
            "first_vault",
            "fv",
            bunny.address,
            WEEK,
            sender=gov,
        )

    tx = vault_factory.deploy_new_vault(
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        WEEK,
        sender=gov,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address

    # Can't reinitialze a new vault.
    with ape.reverts("initialized"):
        new_vault.initialize(
            asset.address,
            "first_vault",
            "fv",
            bunny.address,
            WEEK,
            sender=gov,
        )
