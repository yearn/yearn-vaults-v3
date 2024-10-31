from ape import project, accounts, Contract, chain, networks
from hexbytes import HexBytes
import hashlib


def deploy_original_and_factory():
    print("Deploying Vault Factory on ChainID", chain.chain_id)

    if input("Do you want to continue? ") == "n":
        return

    deployer = input("Name of account to use? ")
    deployer = accounts.load(deployer)

    vault_factory = project.VaultFactory
    vault = project.VaultV3

    deployer_contract = project.IDeployer.at(
        "0xba5Ed099633D3B313e4D5F7bdc1305d3c28ba5Ed"
    )

    salt_string = ""

    # Create a SHA-256 hash object
    hash_object = hashlib.sha256()
    # Update the hash object with the string data
    hash_object.update(salt_string.encode("utf-8"))
    # Get the hexadecimal representation of the hash
    hex_hash = hash_object.hexdigest()
    # Convert the hexadecimal hash to an integer
    salt = 0  # int(hex_hash, 16)

    print(f"Salt we are using {salt}")
    print("Init balance:", deployer.balance / 1e18)
    print("------------------")
    print(f"Deploying Original...")

    original_deploy_bytecode = vault.contract_type.deployment_bytecode.bytecode

    original_tx = deployer_contract.deployCreate2(
        salt, original_deploy_bytecode, sender=deployer
    )

    original_event = list(original_tx.decode_logs(deployer_contract.ContractCreation))

    original_address = original_event[0].newContract

    print(f"Deployed the vault original to {original_address}")
    print("------------------")

    # deploy factory
    print(f"Deploying factory...")

    init_gov = "0x6f3cBE2ab3483EC4BA7B672fbdCa0E9B33F88db8"

    factory_constructor = vault_factory.constructor.encode_input(
        "Yearn v3.0.4 Vault Factory",
        original_address,
        init_gov,
    )

    factory_deploy_bytecode = HexBytes(
        HexBytes(vault_factory.contract_type.deployment_bytecode.bytecode)
        + factory_constructor
    )

    factory_tx = deployer_contract.deployCreate2(
        salt, factory_deploy_bytecode, sender=deployer
    )

    factory_event = list(factory_tx.decode_logs(deployer_contract.ContractCreation))

    factory_address = factory_event[0].newContract

    print(f"Deployed Vault Factory to {factory_address}")
    print("------------------")
    print(f"Encoded Constructor to use for verifaction {factory_constructor.hex()[2:]}")


def main():
    deploy_original_and_factory()
