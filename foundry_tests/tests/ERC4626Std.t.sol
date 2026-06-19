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
    function test_previewDeposit(Init memory init, uint256 assets) public override {
        if (assets == type(uint256).max) assets -= 1;
        super.test_previewDeposit(init, assets);
    }

    function test_deposit(Init memory init, uint256 assets, uint256 allowance) public override {
        if (assets == type(uint256).max) assets -= 1;
        super.test_deposit(init, assets, allowance);
    }

    function test_RevertWhen_withdrawWithoutAllowance(Init memory init, uint256 assets) public {
        setUpVault(init);
        address caller = init.user[0];
        address receiver = init.user[1];
        address owner = init.user[2];
        assets = bound(assets, 0, _max_withdraw(owner));
        vm.assume(caller != owner);
        vm.assume(assets > 0);
        _approve(_vault_, owner, caller, 0);
        vm.prank(caller);
        vm.expectRevert();
        IERC4626(_vault_).withdraw(assets, receiver, owner);
    }

    function test_RevertWhen_redeemWithoutAllowance(Init memory init, uint256 shares) public {
        setUpVault(init);
        address caller = init.user[0];
        address receiver = init.user[1];
        address owner = init.user[2];
        shares = bound(shares, 0, _max_redeem(owner));
        vm.assume(caller != owner);
        vm.assume(shares > 0);
        _approve(_vault_, owner, caller, 0);
        vm.prank(caller);
        vm.expectRevert();
        IERC4626(_vault_).redeem(shares, receiver, owner);
    }

    function clamp(Init memory init, uint256 max) internal pure returns (Init memory) {
        for (uint256 i = 0; i < N; i++) {
            init.share[i] = init.share[i] % max;
            init.asset[i] = init.asset[i] % max;
        }
        init.yield = init.yield % int256(max);
        return init;
    }
}
