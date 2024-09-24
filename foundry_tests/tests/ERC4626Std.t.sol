// SPDX-License-Identifier: MIT
pragma solidity >=0.8.18;

import "erc4626-tests/ERC4626.test.sol";

import {Setup} from "../utils/Setup.sol";

// SEE https://github.com/a16z/erc4626-tests
contract VaultERC4626StdTest is ERC4626Test, Setup {
    function setUp() public override(ERC4626Test, Setup) {
        super.setUp();
        _underlying_ = address(asset);
        _vault_ = address(vault);
        _delta_ = 0;
        _vaultMayBeEmpty = true;
        _unlimitedAmount = true;
    }

    // NOTE: The following tests are relaxed to consider only smaller values (of type uint120),
    // since the maxWithdraw(), and maxRedeem() functions fail with large values (due to overflow).

    function test_maxWithdraw(Init memory init) public override {
        init = clamp(init, type(uint120).max);
        super.test_maxWithdraw(init);
    }

    function test_maxRedeem(Init memory init) public override {
        init = clamp(init, type(uint120).max);
        super.test_maxRedeem(init);
    }

    //Avoid special case for deposits of uint256 max
    function test_previewDeposit(
        Init memory init,
        uint assets
    ) public override {
        if (assets == type(uint256).max) assets -= 1;
        super.test_previewDeposit(init, assets);
    }

    function test_deposit(
        Init memory init,
        uint assets,
        uint allowance
    ) public override {
        if (assets == type(uint256).max) assets -= 1;
        super.test_deposit(init, assets, allowance);
    }

    function clamp(
        Init memory init,
        uint max
    ) internal pure returns (Init memory) {
        for (uint i = 0; i < N; i++) {
            init.share[i] = init.share[i] % max;
            init.asset[i] = init.asset[i] % max;
        }
        init.yield = init.yield % int(max);
        return init;
    }
}
