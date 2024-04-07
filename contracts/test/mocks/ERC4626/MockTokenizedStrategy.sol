// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.8.18;

import {TokenizedStrategy, ERC20} from "@tokenized-strategy/TokenizedStrategy.sol";

contract MockTokenizedStrategy is TokenizedStrategy {
    uint256 public minDebt;
    uint256 public maxDebt = type(uint256).max;

    constructor(
        address _factory,
        address _asset,
        string memory _name,
        address _management,
        address _keeper
    ) TokenizedStrategy(_factory) {
        // Cache storage pointer
        StrategyData storage S = _strategyStorage();

        // Set the strategy's underlying asset
        S.asset = ERC20(_asset);
        // Set the Strategy Tokens name.
        S.name = _name;
        // Set decimals based off the `asset`.
        S.decimals = ERC20(_asset).decimals();

        // Set last report to this block.
        S.lastReport = uint96(block.timestamp);

        // Set the default management address. Can't be 0.
        require(_management != address(0), "ZERO ADDRESS");
        S.management = _management;
        S.performanceFeeRecipient = _management;
        // Set the keeper address
        S.keeper = _keeper;
    }

    function setMinDebt(uint256 _minDebt) external {
        minDebt = _minDebt;
    }

    function setMaxDebt(uint256 _maxDebt) external {
        maxDebt = _maxDebt;
    }

    function availableDepositLimit(
        address
    ) public view virtual returns (uint256) {
        uint256 _totalAssets = _strategyStorage().totalAssets;
        uint256 _maxDebt = maxDebt;
        return _maxDebt > _totalAssets ? _maxDebt - _totalAssets : 0;
    }

    function availableWithdrawLimit(
        address /*_owner*/
    ) public view virtual returns (uint256) {
        return type(uint256).max;
    }

    function deployFunds(uint256 _amount) external virtual {}

    function freeFunds(uint256 _amount) external virtual {}

    function harvestAndReport() external virtual returns (uint256) {
        return _strategyStorage().asset.balanceOf(address(this));
    }
}
