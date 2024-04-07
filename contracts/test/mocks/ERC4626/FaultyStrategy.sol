// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.8.18;

import {ERC4626BaseStrategyMock, IERC20} from "./BaseStrategyMock.sol";

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

contract ERC4626FaultyStrategy is ERC4626BaseStrategyMock {
    constructor(
        address _vault,
        address _asset
    ) ERC4626BaseStrategyMock(_vault, _asset) {}

    // doesn't do anything in liquid strategy as all funds are free
    function _freeFunds(
        uint256 _amount
    ) internal override returns (uint256 _amountFreed) {
        _amountFreed = IERC20(asset()).balanceOf(address(this));
    }

    function maxWithdraw(
        address _owner
    ) public view override returns (uint256) {
        return _convertToAssets(balanceOf(_owner), Math.Rounding.Down);
    }

    function deposit(
        uint256 _assets,
        address _receiver
    ) public override returns (uint256) {
        require(
            _assets <= maxDeposit(_receiver),
            "ERC4626: deposit more than max"
        );

        // this will simulate the strategy only depositing half of what the vault wants to
        uint256 toDeposit = _assets / 2;
        uint256 shares = previewDeposit(toDeposit);
        _deposit(_msgSender(), _receiver, toDeposit, shares);

        return shares;
    }

    function withdraw(
        uint256 _assets,
        address _receiver,
        address _owner
    ) public override returns (uint256) {
        require(
            _assets <= maxWithdraw(_owner),
            "ERC4626: withdraw more than max"
        );

        // this will simulate withdrawing less than the vault wanted to
        uint256 toWithdraw = _assets / 2;
        uint256 shares = previewWithdraw(toWithdraw);
        _withdraw(_msgSender(), _receiver, _owner, toWithdraw, shares);

        return shares;
    }

    function redeem(
        uint256 _shares,
        address _receiver,
        address _owner
    ) public override returns (uint256) {
        require(
            _shares <= maxRedeem(_owner),
            "ERC4626: withdraw more than max"
        );

        // this will simulate withdrawing less than the vault wanted to
        uint256 toRedeem = _shares / 2;
        uint256 assets = previewRedeem(toRedeem);
        _withdraw(_msgSender(), _receiver, _owner, toRedeem, assets);

        return assets;
    }
}
