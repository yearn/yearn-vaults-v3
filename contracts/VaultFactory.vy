# @version 0.3.4

from vyper.interfaces import ERC20

# FUNCTIONS #
@external
def deployNewVault(blueprint: address, asset: ERC20, name: String[64], symbol: String[32], role_manager: address, profit_max_unlock_time: uint256) -> address:
    # blueprint_prefix: b"\xfe\71\x00" -> len=3 following EIP-5202
    return create_from_blueprint(blueprint, asset, name, symbol, role_manager, profit_max_unlock_time, code_offset=3, salt=keccak256(_abi_encode(asset.address, name, symbol)))

@view
@external
def test() -> uint256:
    return 123
