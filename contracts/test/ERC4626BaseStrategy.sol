// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.18;

import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {IERC20Metadata} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IVault} from "../interfaces/IVault.sol";

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

abstract contract ERC4626BaseStrategy is ERC4626 {
    using SafeERC20 for IERC20;

    address public vault;
    uint8 private _decimals;
    address public keeper;

    constructor(
        address _vault,
        address _asset
    ) ERC4626(IERC20(address(_asset))) {
        _initialize(_vault, _asset);
    }

    function _initialize(address _vault, address _asset) internal {
        _decimals = IERC20Metadata(address(_asset)).decimals();

        vault = _vault;
    }

    function decimals() public view virtual override returns (uint8) {
        return _decimals;
    }

    function invest() external virtual {}

    function freeFunds(
        uint256 _amount
    ) external virtual returns (uint256 _freedFunds) {}

    function _invest() internal virtual;

    function _freeFunds(
        uint256 _amount
    ) internal virtual returns (uint256 amountFreed);

    function sweep(address _token) external {}

    function report() external virtual returns (uint256, uint256) {
        return (0, 0);
    }
}
