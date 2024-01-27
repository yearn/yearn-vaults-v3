from ape import project, accounts, Contract, chain, networks
from ape.utils import ZERO_ADDRESS
from web3 import Web3, HTTPProvider
from hexbytes import HexBytes
import os
import hashlib
from copy import deepcopy

# Add the wallet to use here.
deployer = accounts.load("")


def deploy_original_and_factory():
    print("Deploying Vault Factory on ChainID", chain.chain_id)

    if input("Do you want to continue? ") == "n":
        return

    vault_factory = project.VaultFactory
    vault = project.VaultV3
    deployer_contract = project.IDeployer.at(
        "0x8D85e7c9A4e369E53Acc8d5426aE1568198b0112"
    )
    salt_string = "v3.0.2"

    # Create a SHA-256 hash object
    hash_object = hashlib.sha256()
    # Update the hash object with the string data
    hash_object.update(salt_string.encode("utf-8"))
    # Get the hexadecimal representation of the hash
    hex_hash = hash_object.hexdigest()
    # Convert the hexadecimal hash to an integer
    salt = int(hex_hash, 16)

    print(f"Salt we are using {salt}")
    print("Init balance:", deployer.balance / 1e18)

    print(f"Deploying Original...")

    original_deploy_bytecode = vault.contract_type.deployment_bytecode.bytecode

    original_tx = deployer_contract.deploy(
        original_deploy_bytecode, salt, sender=deployer
    )

    original_event = list(original_tx.decode_logs(deployer_contract.Deployed))

    original_address = original_event[0].addr

    print(f"Deployed the vault original to {original_address}")

    # deploy factory
    print(f"Deploying factory...")

    factory_constructor = vault_factory.constructor.encode_input(
        "Yearn v3.0.2 Vault Factory",
        original_address,
        "0x33333333D5eFb92f19a5F94a43456b3cec2797AE",
    )

    factory_deploy_bytecode = HexBytes(
        HexBytes(vault_factory.contract_type.deployment_bytecode.bytecode)
        + factory_constructor
    )

    factory_tx = deployer_contract.deploy(
        factory_deploy_bytecode, salt, sender=deployer
    )

    factory_event = list(factory_tx.decode_logs(deployer_contract.Deployed))

    factory_address = factory_event[0].addr

    print(f"Deployed Vault Factory to {factory_address}")


def main():
    deploy_original_and_factory()
