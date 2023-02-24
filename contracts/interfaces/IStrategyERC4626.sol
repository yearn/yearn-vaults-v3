// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

interface IStrategyERC4626 {
    // So indexers can keep track of this
    // ****** EVENTS ******

    error NoAccess();

    error ProtectedToken(address token);

    error StrategyAlreadyInitialized();

    function vault() external view returns (address _vault);

    // - `invest()`: strategy will invest loose funds into the strategy. only callable by keepers
    function invest() external;

    // - `freeFunds(uint256 _amount)`: strategy will free/unlocked funds from the underlying protocol and leave them idle. (called by vault on update_debt)
    function freeFunds(uint256 _amount) external returns (uint256 _freeFunds);

    function delegatedAssets() external view returns (uint256 _delegatedAssets);

    function migrate(address) external;
}
