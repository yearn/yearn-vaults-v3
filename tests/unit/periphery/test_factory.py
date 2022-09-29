from web3 import Web3, EthereumTesterProvider
from ape import project
from hexbytes import HexBytes
from eth_tester import EthereumTester
import json

def test_factory(gov, asset):
    vault = project.VaultV3

    initcode_prefix = b"\xfe\71\x00"
    bytecode = HexBytes(initcode_prefix) + HexBytes(vault.contract_type.get_runtime_bytecode())
    bytecode_len = len(bytecode)
    bytecode_len_hex = hex(bytecode_len)[2:].rjust(4, "0")
    deploy_preamble = HexBytes("61" + bytecode_len_hex + "3d81600a3d39f3")
    deploy_bytecode = HexBytes(deploy_preamble) + bytecode

    deployer_abi = []

    tester = EthereumTester()
    w3 = Web3(EthereumTesterProvider(tester))

    c = w3.eth.contract(abi=deployer_abi, bytecode=deploy_bytecode)

    deploy_transaction = c.constructor()
    # tx_info = {"from": gov, "value": 0}
    # tx_hash = deploy_transaction.transact(tx_info)
    tx_hash = deploy_transaction.transact()
    blueprint_address = w3.eth.get_transaction_receipt(tx_hash)["contractAddress"]

    # factory = gov.deploy(project.VaultFactory)

    # new_vault = factory.deployNewVault(blueprint_address, asset.address, "test_vault", "tv", gov, 0, sender=gov)

    vault_factory = project.VaultFactory

    c = w3.eth.contract(abi=json.loads(vault_factory.contract_type.json())["abi"], bytecode=vault_factory.contract_type.get_runtime_bytecode())
    deploy_transaction = c.constructor()

    # tx_info = {"from": gov, "value": 0}
    # tx_hash = deploy_transaction.transact(tx_info)

    # tx_hash = deploy_transaction.transact()
    factory_address = w3.eth.get_transaction_receipt(tx_hash)["contractAddress"]



    assert 0
