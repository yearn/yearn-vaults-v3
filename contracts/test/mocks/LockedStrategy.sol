// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {BaseStrategy, IERC20} from "../BaseStrategy.sol";

contract LockedStrategy is BaseStrategy {

  // error for test function setLockedFunds
  error InsufficientFunds();

  uint256 public lockedBalance;
  uint256 public lockedUntil;

  constructor(address _vault) BaseStrategy(_vault) {}

  function name() external view override returns (string memory _name) {}

  // only used during testing
  // locks funds for duration _lockTime
  function setLockedFunds(uint256 _amount, uint256 _lockTime) external {
    uint256 balance = IERC20(asset).balanceOf(address(this));
    if (_amount > balance) revert InsufficientFunds();
    lockedBalance = _amount;
    lockedUntil = block.timestamp + _lockTime;
  }

  // only used during testing
  // free locked funds if duration has passed
  function freeLockedFunds() external {
    if (block.timestamp >= lockedUntil) {
      lockedBalance = 0;
      lockedUntil = 0;
    }
  }

  function _emergencyFreeFunds(uint256 _amountToWithdraw) internal override {}

  function _invest() internal override {}

  function _harvest() internal override {}

  function _freeFunds(uint256 _amount) internal override returns (uint256 _amountFreed) {}

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
    uint256 balance = IERC20(asset).balanceOf(address(this));
    if (block.timestamp < lockedUntil) {
      _withdrawable = balance - lockedBalance;
    } else {
      // no locked assets, withdraw all
      _withdrawable = balance;
    }
  }

  function delegatedAssets() external view override returns (uint256 _delegatedAssets) {}

  function _protectedTokens() internal view override returns (address[] memory _protected) {}
}
