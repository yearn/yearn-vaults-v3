// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {ERC4626BaseStrategyMock, IERC20} from "./BaseStrategyMock.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract ERC4626LossyStrategy is ERC4626BaseStrategyMock {
    using SafeERC20 for IERC20;

    int256 public withdrawingLoss;
    uint256 public lockedFunds;

    constructor(
        address _vault,
        address _asset
    ) ERC4626BaseStrategyMock(_vault, _asset) {}

    // used to generate losses, accepts single arg to send losses to
    function setLoss(address _target, uint256 _loss) external {
        IERC20(asset()).safeTransfer(_target, _loss);
    }

    function setWithdrawingLoss(int256 _loss) external {
        withdrawingLoss = _loss;
    }

    function setLockedFunds(uint256 _lockedFunds) external {
        lockedFunds = _lockedFunds;
    }

    function totalAssets() public view override returns (uint256) {
        if (withdrawingLoss < 0) {
            return uint256(int256(IERC20(asset()).balanceOf(address(this))) + withdrawingLoss);
        } else {
            return super.totalAssets();
        }
    }

    function _withdraw(
        address _caller,
        address _receiver,
        address _owner,
        uint256 _assets,
        uint256 _shares
    ) internal override {
        if (_caller != _owner) {
            _spendAllowance(_owner, _caller, _shares);
        }

        uint256 toWithdraw = uint256(int256(_assets) - withdrawingLoss);
        _burn(_owner, _shares);
        // Withdrawing loss simulates a loss while withdrawing
        IERC20(asset()).safeTransfer(_receiver, toWithdraw);
        if(withdrawingLoss > 0) {
            // burns (to simulate loss while withdrawing)
            IERC20(asset()).safeTransfer(asset(), uint256(withdrawingLoss));
        }

        emit Withdraw(
            _caller,
            _receiver,
            _owner,
            toWithdraw,
            _shares
        );
    }

    function _freeFunds(
        uint256 _amount
    ) internal override returns (uint256 _amountFreed) {}

    function maxWithdraw(address) public view override returns (uint256) {
        return IERC20(asset()).balanceOf(address(this)) - lockedFunds;
    }

    function maxRedeem(address) public view override returns (uint256) {
        return convertToShares(IERC20(asset()).balanceOf(address(this)) - lockedFunds);
    }
}
