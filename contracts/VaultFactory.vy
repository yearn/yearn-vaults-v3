# @version 0.3.7

from vyper.interfaces import ERC20

event NewVault:
    vault_address: indexed(address)
    asset: indexed(address)

event UpdateProtocolFeeBps:
    old_fee_bps: uint16
    new_fee_bps: uint16

event UpdateProtocolFeeRecipient:
    old_fee_recipient: indexed(address)
    new_fee_recipient: indexed(address)

event UpdateGovernance:
    governance: indexed(address)

event NewPendingGovernance:
    pending_governance: indexed(address)

struct PFConfig:
  fee_bps: uint16
  fee_last_change: uint32
  fee_recipient: address

MAX_FEE_BPS: constant(uint16) = 25 # max protocol management fee is 0.25% annual

VAULT_BLUEPRINT: immutable(address)

governance: public(address)
pending_governance: public(address)

name: public(String[64])
protocol_fee_config: public(PFConfig)

@external
def __init__(name: String[64], vault_blueprint: address):
    self.name = name
    VAULT_BLUEPRINT = vault_blueprint
    self.governance = msg.sender

@external
def deploy_new_vault(asset: ERC20, name: String[64], symbol: String[32], role_manager: address, profit_max_unlock_time: uint256) -> address:
    vault_address: address = create_from_blueprint(VAULT_BLUEPRINT, asset, name, symbol, role_manager, profit_max_unlock_time, code_offset=3, salt=keccak256(_abi_encode(msg.sender, asset.address, name, symbol)))
    log NewVault(vault_address, convert(asset, address)
    return vault_address

@view
@external
def vault_blueprint()-> address:
    return VAULT_BLUEPRINT

@external
def set_protocol_fee_bps(new_protocol_fee_bps: uint16):
    assert msg.sender == self.governance, "not governance"
    assert new_protocol_fee_bps <= MAX_FEE_BPS, "fee too high"

    log UpdateProtocolFeeBps(self.protocol_fee_config.fee_bps, new_protocol_fee_bps)

    self.protocol_fee_config.fee_bps = new_protocol_fee_bps
    self.protocol_fee_config.fee_last_change = convert(block.timestamp, uint32)  

@external
def set_protocol_fee_recipient(new_protocol_fee_recipient: address):
    assert msg.sender == self.governance, "not governance"
    log UpdateProtocolFeeRecipient(self.protocol_fee_config.fee_recipient, new_protocol_fee_recipient)
    self.protocol_fee_config.fee_recipient = new_protocol_fee_recipient

@external
def set_governance(new_governance: address):
    assert msg.sender == self.governance, "not governance"
    log NewPendingGovernance(new_governance)
    self.pending_governance = new_governance

@external
def accept_governance():
    assert msg.sender == self.pending_governance, "not pending governance"
    self.governance = msg.sender
    log UpdateGovernance(msg.sender)
    self.pending_governance = ZERO_ADDRESS

