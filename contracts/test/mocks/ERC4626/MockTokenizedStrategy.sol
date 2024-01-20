// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.18;

import {TokenizedStrategy, ERC20} from "@tokenized-strategy/TokenizedStrategy.sol";

contract MockTokenizedStrategy is TokenizedStrategy {
    uint256 public minDebt;
    uint256 public maxDebt = type(uint256).max;

    // Private variables and functions used in this mock.
    bytes32 public constant BASE_STRATEGY_STORAGE =
        bytes32(uint256(keccak256("yearn.base.strategy.storage")) - 1);

    function strategyStorage() internal pure returns (StrategyData storage S) {
        // Since STORAGE_SLOT is a constant, we have to put a variable
        // on the stack to access it from an inline assembly block.
        bytes32 slot = BASE_STRATEGY_STORAGE;
        assembly {
            S.slot := slot
        }
    }

    constructor(
        address _asset,
        string memory _name,
        address _management,
        address _keeper
    ) {
        // Cache storage pointer
        StrategyData storage S = strategyStorage();

        // Set the strategy's underlying asset
        S.asset = ERC20(_asset);
        // Set the Strategy Tokens name.
        S.name = _name;
        // Set decimals based off the `asset`.
        S.decimals = ERC20(_asset).decimals();

        // Set last report to this block.
        S.lastReport = uint128(block.timestamp);

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
        uint256 _totalAssets = totalAssets();
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
        return strategyStorage().asset.balanceOf(address(this));
    }
}
