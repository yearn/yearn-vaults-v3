// SPDX-License-Identifier: MIT
pragma solidity 0.8.18;

import "erc4626-tests/ERC4626.test.sol";

import {Setup} from "./utils/Setup.sol";

// SEE https://github.com/a16z/erc4626-tests
contract ERC4626StdTest is ERC4626Test, Setup {
    function setUp() public override(ERC4626Test, Setup) {
        super.setUp();
        _underlying_ = address(asset);
        _vault_ = address(strategy);
        _delta_ = 0;
        _vaultMayBeEmpty = true;
        _unlimitedAmount = true;
    }
}
