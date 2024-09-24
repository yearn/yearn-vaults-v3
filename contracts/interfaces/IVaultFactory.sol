// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.8.18;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

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
    event UpdatePendingGovernance(address newPendingGovernance);
    event GovernanceTransferred(
        address previousGovernance,
        address newGovernance
    );

    function shutdown() external view returns (bool);

    function governance() external view returns (address);

    function pendingGovernance() external view returns (address);

    function name() external view returns (string memory);

    function use_custom_protocol_fee(address) external view returns (bool);

    function deploy_new_vault(
        address asset,
        string memory name,
        string memory symbol,
        address role_manager,
        uint256 profit_max_unlock_time
    ) external returns (address);

    function vault_original() external view returns (address);

    function apiVersion() external view returns (string memory);

    function protocol_fee_config()
        external
        view
        returns (uint16 fee_bps, address fee_recipient);

    function protocol_fee_config(
        address vault
    ) external view returns (uint16 fee_bps, address fee_recipient);

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

    function transferGovernance(address new_governance) external;

    function acceptGovernance() external;
}
