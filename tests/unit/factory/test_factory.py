from ape import project, reverts


def test_new_vault_with_different_salt(
    gov, asset, bunny, fish, vault_factory, vault_blueprint
):
    assert vault_factory.name() == "Vault V3 Factory"

    tx = vault_factory.deploy_new_vault(
        vault_blueprint,
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        0,
        sender=gov,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address

    tx = vault_factory.deploy_new_vault(
        vault_blueprint,
        asset.address,
        "second_vault",
        "sv",
        fish.address,
        0,
        sender=gov,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "second_vault"
    assert new_vault.role_manager() == fish.address


def test_new_vault_same_name_asset_and_symbol_different_sender(
    gov, asset, bunny, vault_factory, vault_blueprint
):
    tx = vault_factory.deploy_new_vault(
        vault_blueprint,
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        0,
        sender=gov,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address

    vault_factory.deploy_new_vault(
        vault_blueprint,
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        0,
        sender=bunny,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address


def test_new_vault_same_sender_name_asset_and_symbol__reverts(
    gov, asset, bunny, vault_factory, vault_blueprint
):
    tx = vault_factory.deploy_new_vault(
        vault_blueprint,
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        0,
        sender=gov,
    )
    event = list(tx.decode_logs(vault_factory.NewVault))
    new_vault = project.VaultV3.at(event[0].vault_address)
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address

    with reverts():
        vault_factory.deploy_new_vault(
            vault_blueprint,
            asset.address,
            "first_vault",
            "fv",
            bunny.address,
            0,
            sender=gov,
        )
