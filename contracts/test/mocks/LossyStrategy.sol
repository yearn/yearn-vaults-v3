// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {BaseStrategyMock, IERC20} from "./BaseStrategyMock.sol";

contract LossyStrategy is BaseStrategyMock {

  constructor(address _vault) BaseStrategyMock(_vault) {}

  // used to generate losses, accepts single arg to send losses to
  function setLoss(address _target, uint256 _loss) external {
    IERC20(asset).transfer(_target, _loss);
  }

  function _freeFunds(uint256 _amount) internal override returns (uint256 _amountFreed) {}

  function withdrawable() external view override returns (uint256 _withdrawable) {
    _withdrawable = IERC20(asset).balanceOf(address(this));
  }
}
