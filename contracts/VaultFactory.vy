# @version 0.3.4

from vyper.interfaces import ERC20

event NewVault:
    vault_address: indexed(address)

VAULT_BLUEPRINT: immutable(address)

name: public(String[64])

@external
def __init__(name: String[64], vault_blueprint: address):
    self.name = name
    VAULT_BLUEPRINT = vault_blueprint

@external
def deploy_new_vault(asset: ERC20, name: String[64], symbol: String[32], role_manager: address, profit_max_unlock_time: uint256) -> address:
    vault_address: address = create_from_blueprint(VAULT_BLUEPRINT, asset, name, symbol, role_manager, profit_max_unlock_time, code_offset=3, salt=keccak256(_abi_encode(msg.sender, asset.address, name, symbol)))
    log NewVault(vault_address)
    return vault_address

@view
@external
def vault_blueprint()-> address:
    return VAULT_BLUEPRINT