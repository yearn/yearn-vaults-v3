// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {BaseStrategy, IERC20} from "../BaseStrategy.sol";

contract BaseStrategyLiquid is BaseStrategy {

  error InvalidFee();

  // fee implementation (can be used to represent slippage or asset withdrawal fee)
  // 0 <= fee <= 10000
  uint256 public fee;
  uint256 constant MAX_FEE = 10_000;

  constructor(address _vault) BaseStrategy(_vault) {}

  function name() external view override returns (string memory _name) {}

  function setFee(uint256 _fee) external {
    if (fee < 0 || fee > MAX_FEE) revert InvalidFee();
    fee = _fee;
  }

  function _emergencyFreeFunds(uint256 _amountToWithdraw) internal override {}

  function _invest() internal override {}

  function _harvest() internal override {}

  function _freeFunds(uint256 _amount) internal override returns (uint256 _amountFreed) {
    uint256 penalty = _amount * fee / MAX_FEE;
    _amountFreed = (_amount - penalty);
  }

  function _migrate(address _newStrategy) internal override {}

  function harvestTrigger() external view override returns (bool) {}

  function investTrigger() external view override returns (bool) {}

  function investable() external view override returns (uint256 _minDebt, uint256 _maxDebt) {
    _minDebt = 0;
    _maxDebt = type(uint256).max;
  }

  function totalAssets() external view override returns (uint256) {
    return IERC20(asset).balanceOf(address(this));
  }

  function withdrawable() external view override returns (uint256 _withdrawable) {
    _withdrawable = IERC20(asset).balanceOf(address(this));
  }

  function delegatedAssets() external view override returns (uint256 _delegatedAssets) {}

  function _protectedTokens() internal view override returns (address[] memory _protected) {}
}
