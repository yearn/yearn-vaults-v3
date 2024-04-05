// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.8.18;

import {ERC4626BaseStrategyMock, IERC20} from "./BaseStrategyMock.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract ERC4626LockedStrategy is ERC4626BaseStrategyMock {
    using SafeERC20 for IERC20;
    // error for test function setLockedFunds
    error InsufficientFunds();

    uint256 public lockedBalance;
    uint256 public lockedUntil;

    constructor(
        address _vault,
        address _asset
    ) ERC4626BaseStrategyMock(_vault, _asset) {}

    // only used during testing
    // locks funds for duration _lockTime
    function setLockedFunds(uint256 _amount, uint256 _lockTime) external {
        uint256 balance = IERC20(asset()).balanceOf(address(this));
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

    function _freeFunds(
        uint256 _amount
    ) internal override returns (uint256 _amountFreed) {}

    function maxWithdraw(address) public view override returns (uint256) {
        uint256 balance = IERC20(asset()).balanceOf(address(this));
        if (block.timestamp < lockedUntil) {
            return balance - lockedBalance;
        } else {
            // no locked assets, withdraw all
            return balance;
        }
    }

    function maxRedeem(address) public view override returns (uint256) {
        uint256 balance = IERC20(asset()).balanceOf(address(this));
        if (block.timestamp < lockedUntil) {
            return convertToShares(balance - lockedBalance);
        } else {
            // no locked assets, withdraw all
            return convertToShares(balance);
        }
    }
}
