from web3 import Web3, HTTPProvider
from hexbytes import HexBytes
from ape import project, reverts


def test_new_vault(gov, asset, bunny, fish):
    # we connect to hardhat node
    w3 = Web3(HTTPProvider("http://127.0.0.1:8545"))
    assert w3.isConnected()

    # Prepare blueprint code
    blueprint_preamble = b"\xFE\x71\x00"  # ERC5202 preamble
    blueprint_bytecode = blueprint_preamble + HexBytes(
        project.VaultV3.contract_type.deployment_bytecode.bytecode
    )
    # the length of the deployed code in bytes
    len_bytes = len(blueprint_bytecode).to_bytes(2, "big")
    deploy_bytecode = (
        b"\x61" + len_bytes + b"\x3d\x81\x60\x0a\x3d\x39\xf3"
    )  # Deploy bytecode
    deploy_bytecode = HexBytes(deploy_bytecode + blueprint_bytecode)

    # Deploy blueprint
    deployer_abi = []
    c = w3.eth.contract(abi=deployer_abi, bytecode=deploy_bytecode)
    deploy_transaction = c.constructor()
    tx_info = {"from": gov.address, "value": 0, "gasPrice": 0}
    tx_hash = deploy_transaction.transact(tx_info)
    blueprint_address = w3.eth.get_transaction_receipt(tx_hash)["contractAddress"]

    # Deploy factory
    vault_factory = gov.deploy(project.VaultFactory, "Vault V3 Factory")
    assert vault_factory.name() == "Vault V3 Factory"

    vault_factory.deploy_new_vault(
        blueprint_address,
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        0,
        sender=gov,
    )
    new_vault = project.VaultV3.at(vault_factory.last_deploy())
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address

    vault_factory.deploy_new_vault(
        blueprint_address,
        asset.address,
        "second_vault",
        "sv",
        fish.address,
        0,
        sender=gov,
    )
    new_vault = project.VaultV3.at(vault_factory.last_deploy())
    assert new_vault.name() == "second_vault"
    assert new_vault.role_manager() == fish.address


def test_new_vault_same_name_asset_and_symbol__reverts(gov, asset, bunny, fish):
    # we connect to hardhat node
    w3 = Web3(HTTPProvider("http://127.0.0.1:8545"))
    assert w3.isConnected()

    # Prepare blueprint code
    blueprint_preamble = b"\xFE\x71\x00"  # ERC5202 preamble
    blueprint_bytecode = blueprint_preamble + HexBytes(
        project.VaultV3.contract_type.deployment_bytecode.bytecode
    )
    # the length of the deployed code in bytes
    len_bytes = len(blueprint_bytecode).to_bytes(2, "big")
    deploy_bytecode = (
        b"\x61" + len_bytes + b"\x3d\x81\x60\x0a\x3d\x39\xf3"
    )  # Deploy bytecode
    deploy_bytecode = HexBytes(deploy_bytecode + blueprint_bytecode)

    # Deploy blueprint
    deployer_abi = []
    c = w3.eth.contract(abi=deployer_abi, bytecode=deploy_bytecode)
    deploy_transaction = c.constructor()
    tx_info = {"from": gov.address, "value": 0, "gasPrice": 0}
    tx_hash = deploy_transaction.transact(tx_info)
    blueprint_address = w3.eth.get_transaction_receipt(tx_hash)["contractAddress"]

    # Deploy factory
    vault_factory = gov.deploy(project.VaultFactory, "Vault V3 Factory")
    assert vault_factory.name() == "Vault V3 Factory"

    vault_factory.deploy_new_vault(
        blueprint_address,
        asset.address,
        "first_vault",
        "fv",
        bunny.address,
        0,
        sender=gov,
    )
    new_vault = project.VaultV3.at(vault_factory.last_deploy())
    assert new_vault.name() == "first_vault"
    assert new_vault.role_manager() == bunny.address

    with reverts():
        vault_factory.deploy_new_vault(
            blueprint_address,
            asset.address,
            "first_vault",
            "fv",
            bunny.address,
            0,
            sender=gov,
        )
