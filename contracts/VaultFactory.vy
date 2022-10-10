# @version 0.3.4

from vyper.interfaces import ERC20

event NewVault:
    vault_address: indexed(address)

name: public(String[64])

@external
def __init__(name: String[64]):
    self.name = name

@external
def deploy_new_vault(blueprint: address, asset: ERC20, name: String[64], symbol: String[32], role_manager: address, profit_max_unlock_time: uint256) -> address:
    vault_address: address = create_from_blueprint(blueprint, asset, name, symbol, role_manager, profit_max_unlock_time, code_offset=3, salt=keccak256(_abi_encode(asset.address, name, symbol)))
    log NewVault(vault_address)
    return vault_address
