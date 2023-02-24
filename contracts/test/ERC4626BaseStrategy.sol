// SPDX-License-Identifier: GPL-3.0

pragma solidity 0.8.14;

import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {IERC20Metadata} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IVault} from "../interfaces/IVault.sol";
import {IStrategyERC4626} from "../interfaces/IStrategyERC4626.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

abstract contract ERC4626BaseStrategy is IStrategyERC4626, ERC4626 {
    using SafeERC20 for IERC20;

    address public override vault;
    uint8 private _decimals;

    constructor(address _vault, address _asset)
        ERC4626(IERC20Metadata(address(_asset)))
    {
        _initialize(_vault, _asset);
    }

    function _initialize(address _vault, address _asset) internal {
        _decimals = IERC20Metadata(address(_asset)).decimals();

        vault = _vault;
        //        // using approve since initialization is only called once
        //        IERC20(_asset).approve(_vault, type(uint256).max); // Give Vault unlimited access (might save gas)
    }

    /** @dev See {IERC20Metadata-decimals}. */
    function decimals()
        public
        view
        virtual
        override(ERC20, IERC20Metadata)
        returns (uint8)
    {
        return _decimals;
    }

    // TODO: add roles (including vault)
    // TODO: should we force invest and freeFunds to be in deposit and withdraw functions?

    function invest() external override {
        // TODO: add permissioning ?
    }

    function freeFunds(uint256 _amount)
        external
        override
        returns (uint256 _freedFunds)
    {
        // TODO: add permissioning ?
    }

    function migrate(address _newStrategy) external virtual override {
        // TODO: add permissioning
    }

    function _invest() internal virtual;

    function _freeFunds(uint256 _amount)
        internal
        virtual
        returns (uint256 amountFreed);

    function _protectedTokens()
        internal
        view
        virtual
        returns (address[] memory);

    function sweep(address _token) external {
        // TODO: add permissioning
        // TODO: add logic
    }
}
