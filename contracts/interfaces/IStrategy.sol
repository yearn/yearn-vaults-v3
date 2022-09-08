// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

interface IStrategy {
    // So indexers can keep track of this
    // ****** EVENTS ******

    error NoAccess();

    error ProtectedToken(address token);

    error StrategyAlreadyInitialized();

    /**
     * @notice This Strategy's name.
     * @dev
     *  You can use this field to manage the 'version' of this Strategy, e.g.
     *  `StrategySomethingOrOtherV1`. However, 'API Version' is managed by
     *  `apiVersion()` function above.
     * @return _name This Strategy's name.
     */
    function name() external view returns (string memory _name);

    function apiVersion() external pure returns (uint256);

    function asset() external view returns (address _asset);

    function vault() external view returns (address _vault);

    function harvestTrigger() external view returns (bool);

    function harvest() external;

    // - `withdrawable() -> uint256`: returns amount of funds that can be freed
    function withdrawable() external view returns (uint256 _withdrawable);

    // - manual: called by governance or guard, behaves similarly to freeFunds but can incur in losses.
    // - vault: called by vault.update_debt if vault is on emergencyFreeFunds mode.
    function emergencyFreeFunds(uint256 _amountToWithdraw) external;

    // - `investable() -> uint256`: returns _minDebt, _maxDebt with the min and max amounts that a strategy can invest in the underlying protocol.
    function investable()
        external
        view
        returns (uint256 _minDebt, uint256 _maxDebt);

    // TODO Discuss (mix of totalDebt + freeFunds? kinda)
    function totalAssets() external view returns (uint256 _totalAssets);

    // - `investTrigger() -> bool`: returns true when the strategy has available funds to invest and space for them.
    function investTrigger() external view returns (bool);

    // - `invest()`: strategy will invest loose funds into the strategy. only callable by keepers
    function invest() external;

    // - `freeFunds(uint256 _amount)`: strategy will free/unlocked funds from the underlying protocol and leave them idle. (called by vault on update_debt)
    function freeFunds(uint256 _amount) external returns (uint256 _freeFunds);

    // TODO: do we really need delegatedAssets? most strategies won't use it...
    function delegatedAssets() external view returns (uint256 _delegatedAssets);

    function migrate(address) external;
}
