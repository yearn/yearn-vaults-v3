// SPDX-License-Identifier: GPL-3.0

pragma solidity >=0.8.18;

import {ERC4626} from "@openzeppelin/contracts/token/ERC20/extensions/ERC4626.sol";
import {IERC20Metadata} from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract Generic4626 is ERC4626 {
    constructor(
        address _asset
    ) ERC4626(IERC20Metadata(address(_asset))) ERC20("a", "a") {}
}
