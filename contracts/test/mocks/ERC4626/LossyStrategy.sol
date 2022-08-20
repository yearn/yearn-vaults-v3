// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {ERC4626BaseStrategyMock, IERC20} from "./BaseStrategyMock.sol";

contract ERC4626LossyStrategy is ERC4626BaseStrategyMock {

  constructor(address _vault, address _asset) ERC4626BaseStrategyMock(_vault, _asset) {}

  // used to generate losses, accepts single arg to send losses to
  function setLoss(address _target, uint256 _loss) external {
    IERC20(asset()).transfer(_target, _loss);
  }

  function _freeFunds(uint256 _amount) internal override returns (uint256 _amountFreed) {}

  function maxWithdraw(address) public view override returns (uint256) {
    return IERC20(asset()).balanceOf(address(this));
  }
}
