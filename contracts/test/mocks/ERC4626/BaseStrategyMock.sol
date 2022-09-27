// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {ERC4626BaseStrategy, IERC20} from "../../ERC4626BaseStrategy.sol";
import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

abstract contract ERC4626BaseStrategyMock is ERC4626BaseStrategy {
    using Math for uint256;

    uint256 public minDebt;
    uint256 public maxDebt = type(uint256).max;

    constructor(address _vault, address _asset)
        ERC4626BaseStrategy(_vault, _asset)
        ERC20("a", "a")
    {}

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

    function deposit(uint256 assets, address receiver)
        public
        override
        returns (uint256)
    {
        // transfer and invest
//        IERC20(asset()).transferFrom(receiver, address(this), assets);
        SafeERC20.safeTransferFrom(IERC20(asset()), receiver, address(this), assets);
//        return assets;
        emit n(assets, receiver, address(this));
        return assets;
    }
    event n(uint256 assets, address receiver, address strategy);
}
