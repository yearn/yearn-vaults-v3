// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {BaseStrategyMock, IERC20} from "./BaseStrategyMock.sol";

contract LiquidStrategy is BaseStrategyMock {

  constructor(address _vault) BaseStrategyMock(_vault) {}

  // doesn't do anything in liquid strategy as all funds are free
  function _freeFunds(uint256 _amount) internal override returns (uint256 _amountFreed) {
    _amountFreed = IERC20(asset).balanceOf(address(this));
  }

  function withdrawable() external view override returns (uint256 _withdrawable) {
    _withdrawable = IERC20(asset).balanceOf(address(this));
  }

}
