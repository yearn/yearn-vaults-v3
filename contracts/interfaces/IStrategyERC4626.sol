// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

interface IStrategyERC4626 {
    // So indexers can keep track of this
    // ****** EVENTS ******

    error NoAccess();

    error ProtectedToken(address token);

    error StrategyAlreadyInitialized();

    function vault() external view returns (address _vault);

    function harvestTrigger() external view returns (bool);

    // - manual: called by governance or guard, behaves similarly to freeFunds but can incur in losses.
    // - vault: called by vault.update_debt if vault is on emergencyFreeFunds mode.
    // function emergencyFreeFunds(uint256 _amountToWithdraw) external;

    // - `investTrigger() -> bool`: returns true when the strategy has available funds to invest and space for them.
    function investTrigger() external view returns (bool);

    // - `invest()`: strategy will invest loose funds into the strategy. only callable by keepers
    function invest() external;

    // - `freeFunds(uint256 _amount)`: strategy will free/unlocked funds from the underlying protocol and leave them idle. (called by vault on update_debt)
    function freeFunds(uint256 _amount) external returns (uint256 _freeFunds);

    function delegatedAssets() external view returns (uint256 _delegatedAssets);

    function migrate(address) external;
}
