// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {ERC4626BaseStrategy, IERC20} from "../../ERC4626BaseStrategy.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

abstract contract ERC4626BaseStrategyMock is ERC4626BaseStrategy {
    using Math for uint256;
    using SafeERC20 for IERC20;

    uint256 public minDebt;
    uint256 public maxDebt = type(uint256).max;

    event Tend();

    constructor(address _vault, address _asset)
        ERC4626BaseStrategy(_vault, _asset)
        ERC20("a", "a")
    {}

    function tend() external {
        emit Tend();
    }

    function migrate(address _newStrategy) external override {
        IERC20(asset()).safeTransfer(
            _newStrategy,
            IERC20(asset()).balanceOf(address(this))
        );
    }

    function setMinDebt(uint256 _minDebt) external {
        minDebt = _minDebt;
    }

    function setMaxDebt(uint256 _maxDebt) external {
        maxDebt = _maxDebt;
    }

    function maxDeposit(address) public view override returns (uint256) {
        uint256 _totalAssets = totalAssets();
        uint256 _maxDebt = maxDebt;
        return _maxDebt > _totalAssets ? _maxDebt - _totalAssets : 0;
    }

    function totalAssets() public view override returns (uint256) {
        return IERC20(asset()).balanceOf(address(this));
    }

    // function _emergencyFreeFunds(uint256 _amountToWithdraw) internal override {}

    function _invest() internal override {}

    function harvestTrigger() external view override returns (bool) {}

    function investTrigger() external view override returns (bool) {}

    function delegatedAssets()
        external
        view
        override
        returns (uint256 _delegatedAssets)
    {}

    function _protectedTokens()
        internal
        view
        override
        returns (address[] memory _protected)
    {}
}
