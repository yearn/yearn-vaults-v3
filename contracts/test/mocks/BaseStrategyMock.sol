// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {BaseStrategy, IERC20} from "../BaseStrategy.sol";

abstract contract BaseStrategyMock is BaseStrategy {

  uint256 public minDebt;
  uint256 public maxDebt;

  constructor(address _vault) BaseStrategy(_vault) {}

  function setMinDebt(uint256 _minDebt) external {
    minDebt = _minDebt;
  }

  function setMaxDebt(uint256 _maxDebt) external {
    maxDebt = _maxDebt;
  }

  function investable() external view override returns (uint256 _minDebt, uint256 _maxDebt) {
    _minDebt = minDebt;
    _maxDebt = maxDebt;
  }

  function totalAssets() external view override returns (uint256) {
    return IERC20(asset).balanceOf(address(this));
  }

  function name() external view override returns (string memory _name) {}

  function _emergencyFreeFunds(uint256 _amountToWithdraw) internal override {}

  function _invest() internal override {}

  function _harvest() internal override {}


  function _migrate(address _newStrategy) internal override {}

  function harvestTrigger() external view override returns (bool) {}

  function investTrigger() external view override returns (bool) {}

  function delegatedAssets() external view override returns (uint256 _delegatedAssets) {}

  function _protectedTokens() internal view override returns (address[] memory _protected) {}
}
