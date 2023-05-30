# @version 0.3.7

"""
@title Yearn Vault Factory
@license GNU AGPLv3
@author yearn.finance
"""

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

event UpdateCustomProtocolFee:
    vault: indexed(address)
    new_custom_protocol_fee: uint16

event RemovedCustomProtocolFee:
    vault: indexed(address)

event FactoryShutdown():
    pass

event UpdateGovernance:
    governance: indexed(address)

event NewPendingGovernance:
    pending_governance: indexed(address)

struct PFConfig:
    # Percent of fees payed to Yearn in Basis Points.
    fee_bps: uint16
    # Address for protocol fees to get paid to.
    fee_recipient: address

# The max amount the protocol fee can be set to.
MAX_FEE_BPS: constant(uint16) = 5_000
# Identifier for this version of the vault.
API_VERSION: constant(String[28]) = "3.0.1-beta"

# The address that all newly deployed vaults are based from.
VAULT_BLUEPRINT: immutable(address)

# State of the Factory. If True no new vaults can be deployed.
shutdown: public(bool)

# Address that can set or change the fee configs.
governance: public(address)
# Pending governance waiting to be accepted.
pending_governance: public(address)

# Name for identification.
name: public(String[64])

# The default config for assessing protocol fees.
default_protocol_fee_config: public(PFConfig)
# Custom fee to charge for a specific vault or strategy.
custom_protocol_fee: public(HashMap[address, uint16])
# Repersents if a custom protocol fee should be used.
use_custom_protocol_fee: public(HashMap[address, bool])

@external
def __init__(name: String[64], vault_blueprint: address):
    self.name = name
    VAULT_BLUEPRINT = vault_blueprint
    self.governance = msg.sender

@external
def deploy_new_vault(
    asset: ERC20, 
    name: String[64], 
    symbol: String[32], 
    role_manager: address, 
    profit_max_unlock_time: uint256
) -> address:
    """
    @notice Deploys a new vault
    @param asset The asset to be used for the vault
    @param name The name of the vault
    @param symbol The symbol of the vault
    @param role_manager The address of the role manager
    @param profit_max_unlock_time The maximum time that the profit can be locked for
    @return The address of the new vault
    """
    assert not self.shutdown, "shutdown"

    vault_address: address = create_from_blueprint(
            VAULT_BLUEPRINT, 
            asset, 
            name, 
            symbol, 
            role_manager, 
            profit_max_unlock_time, 
            code_offset=3, 
            salt=keccak256(_abi_encode(msg.sender, asset.address, name, symbol))
        )
        
    log NewVault(vault_address, asset.address)
    return vault_address

@view
@external
def vault_blueprint()-> address:
    """
    @notice Get the address of the vault blueprint
    @return The address of the vault blueprint
    """
    return VAULT_BLUEPRINT

@view
@external
def api_version() -> String[28]:
    """
    @notice Get the API version of the factory.
    @return The API version of the factory.
    """
    return API_VERSION

@view
@external
def protocol_fee_config() -> PFConfig:
    """
    @notice Called during vault and strategy reports 
    to retreive the protocol fee to charge and address
    to receive the fees.
    @return The protocol fee config for the msg sender
    """
    # If there is a custom protocol fee set we return it.
    if self.use_custom_protocol_fee[msg.sender]:
        # Always use the default fee recipient even with custom fees.
        return PFConfig({
            fee_bps: self.custom_protocol_fee[msg.sender],
            fee_recipient: self.default_protocol_fee_config.fee_recipient
        })
    else:
        # Otherwise return the default config.
        return self.default_protocol_fee_config

@external
def set_protocol_fee_bps(new_protocol_fee_bps: uint16):
    """
    @notice Set the protocol fee in basis points
    @dev Must be below the max allowed fee, and a default
    fee_recipient must be set so we don't issue fees to the 0 addresss.
    @param new_protocol_fee_bps The new protocol fee in basis points
    """
    assert msg.sender == self.governance, "not governance"
    assert new_protocol_fee_bps <= MAX_FEE_BPS, "fee too high"
    assert self.default_protocol_fee_config.fee_recipient != empty(address), "no recipient"

    log UpdateProtocolFeeBps(
        self.default_protocol_fee_config.fee_bps, 
        new_protocol_fee_bps
    )

    self.default_protocol_fee_config.fee_bps = new_protocol_fee_bps

@external
def set_protocol_fee_recipient(new_protocol_fee_recipient: address):
    """
    @notice Set the protocol fee recipient
    @param new_protocol_fee_recipient The new protocol fee recipient
    """
    assert msg.sender == self.governance, "not governance"
    assert new_protocol_fee_recipient != empty(address), "zero address"

    log UpdateProtocolFeeRecipient(
        self.default_protocol_fee_config.fee_recipient,
        new_protocol_fee_recipient
    )
    
    self.default_protocol_fee_config.fee_recipient = new_protocol_fee_recipient

@external
def set_custom_protocol_fee_bps(vault: address, new_custom_protocol_fee: uint16):
    """
    @notice Allows Governance to set custom protocol fees
    for a specific vault or strategy.
    @dev Must be below the max allowed fee, and a default
    fee_recipient must be set so we don't issue fees to the 0 addresss.
    @param vault The address of the vault or strategy to customize.
    @param new_custom_protocol_fee The custom protocol fee in BPS.
    """
    assert msg.sender == self.governance, "not governance"
    assert new_custom_protocol_fee <= MAX_FEE_BPS, "fee too high"
    assert self.default_protocol_fee_config.fee_recipient != empty(address), "no recipient"

    self.custom_protocol_fee[vault] = new_custom_protocol_fee

    # If this is the first time a custom fee is set for this vault
    # set the bool indicator so it returns the correct fee.
    if not self.use_custom_protocol_fee[vault]:
        self.use_custom_protocol_fee[vault] = True

    log UpdateCustomProtocolFee(vault, new_custom_protocol_fee)

@external 
def remove_custom_protocol_fee(vault: address):
    """
    @notice Allows governance to remove a previously set
    custom protocol fee.
    @param vault The address of the vault or strategy to
    remove the custom fee for.
    """
    assert msg.sender == self.governance, "not governance"

    # Reset the custom fee to 0.
    self.custom_protocol_fee[vault] = 0

    # Set custom fee bool back to false.
    self.use_custom_protocol_fee[vault] = False

    log RemovedCustomProtocolFee(vault)

@external
def shutdown_factory():
    """
    @notice To stop new deployments through this factory.
    @dev A one time switch available for governance to stop
    new vaults from being deployed through the factory.
    NOTE: This will have no effect on any previously deployed
    vaults that deployed from this factory.
    """
    assert msg.sender == self.governance, "not governance"
    assert self.shutdown == False, "shutdown"

    self.shutdown = True
    
    log FactoryShutdown()

@external
def set_governance(new_governance: address):
    """
    @notice Set the governance address
    @param new_governance The new governance address
    """
    assert msg.sender == self.governance, "not governance"
    self.pending_governance = new_governance

    log NewPendingGovernance(new_governance)

@external
def accept_governance():
    """
    @notice Accept the governance address
    """
    assert msg.sender == self.pending_governance, "not pending governance"
    self.governance = msg.sender
    self.pending_governance = empty(address)

    log UpdateGovernance(msg.sender)

