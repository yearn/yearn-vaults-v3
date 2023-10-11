// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.18;

interface IVaultFactory {
    event NewVault(address indexed vaultAddress, address indexed asset);
    event UpdateProtocolFeeBps(
        uint16 oldProtocolFeeBps,
        uint16 newProtocolFeeBps
    );
    event UpdateProtocolFeeRecipient(
        address oldProtocolFeeRecipient,
        address newProtocolFeeRecipient
    );
    event UpdateCustomProtocolFee(address vault, uint16 newCustomProtocolFee);
    event RemovedCustomProtocolFee(address vault);
    event FactoryShutdown();
    event NewPendingGovernance(address newPendingGovernance);
    event UpdateGovernance(address newGovernance);

    function deploy_new_vault(
        address asset,
        string memory name,
        string memory symbol,
        address role_manager,
        uint256 profit_max_unlock_time
    ) external returns (address);

    function vault_blueprint() external view returns (address);

    function api_version() external view returns (string memory);

    function protocol_fee_config()
        external
        view
        returns (uint16 fee_bps, address fee_recipient);

    function set_protocol_fee_bps(uint16 new_protocol_fee_bps) external;

    function set_protocol_fee_recipient(
        address new_protocol_fee_recipient
    ) external;

    function set_custom_protocol_fee_bps(
        address vault,
        uint16 new_custom_protocol_fee
    ) external;

    function remove_custom_protocol_fee(address vault) external;

    function shutdown_factory() external;

    function set_governance(address new_governance) external;

    function accept_governance() external;
}
