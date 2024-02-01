// SPDX-License-Identifier: MIT
pragma solidity 0.8.18;

import "erc4626-tests/ERC4626.test.sol";

import {Setup, IVault} from "./utils/Setup.sol";

contract Testin is Setup {

    function setUp() public override {
        super.setUp();
    }

    function test_set() public {
        vault = IVault(setUpVault());
    }
}