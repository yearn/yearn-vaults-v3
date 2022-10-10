# @version 0.3.4

from vyper.interfaces import ERC20

name: public(String[64])
# TODO: think whether to return value, emit Event or save in storage
last_deploy: public(address)

@external
def __init__(name: String[64]):
    self.name = name

@external
def deploy_new_vault(blueprint: address, asset: ERC20, name: String[64], symbol: String[32], role_manager: address, profit_max_unlock_time: uint256):
    self.last_deploy = create_from_blueprint(blueprint, asset, name, symbol, role_manager, profit_max_unlock_time, code_offset=3, salt=keccak256(_abi_encode(asset.address, name, symbol)))
