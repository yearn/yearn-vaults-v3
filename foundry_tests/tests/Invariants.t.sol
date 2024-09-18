// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.18;

import "forge-std/console.sol";
import {BaseInvariant} from "../utils/BaseInvariant.sol";
import {VaultHandler} from "../handlers/VaultHandler.sol";

contract VaultInvariantTest is BaseInvariant {
    VaultHandler public vaultHandler;

    function setUp() public override {
        super.setUp();

        vaultHandler = new VaultHandler();

        excludeSender(address(0));
        excludeSender(address(vault));
        excludeSender(address(asset));
        excludeSender(address(strategy));

        targetContract(address(vaultHandler));

        targetSelector(
            FuzzSelector({
                addr: address(vaultHandler),
                selectors: getTargetSelectors()
            })
        );
    }

    function invariant_totalAssets() public {
        assert_totalAssets(
            vaultHandler.ghost_depositSum(),
            vaultHandler.ghost_withdrawSum(),
            vaultHandler.ghost_profitSum(),
            vaultHandler.ghost_lossSum()
        );
    }

    function invariant_maxWithdraw() public {
        assert_maxWithdraw(vaultHandler.unreported());
    }

    function invariant_maxRedeem() public {
        assert_maxRedeem(vaultHandler.unreported());
    }

    function invariant_maxWithdrawEqualsMaxRedeem() public {
        assert_maxRedeemEqualsMaxWithdraw(vaultHandler.unreported());
    }

    function invariant_unlockingTime() public {
        assert_unlockingTime();
    }

    function invariant_unlockedShares() public {
        assert_unlockedShares();
    }

    function invariant_previewMintAndConvertToAssets() public {
        assert_previewMintAndConvertToAssets();
    }

    function invariant_previewWithdrawAndConvertToShares() public {
        assert_previewWithdrawAndConvertToShares();
    }

    function invariant_balanceAndTotalAssets() public {
        assert_balanceAndTotalAssets(vaultHandler.unreported());
    }

    function invariant_totalDebt() public {
        assert_totalDebt(vaultHandler.unreported());
    }

    function invariant_callSummary() public view {
        vaultHandler.callSummary();
    }

    function getTargetSelectors()
        internal
        view
        returns (bytes4[] memory selectors)
    {
        selectors = new bytes4[](12);
        selectors[0] = vaultHandler.deposit.selector;
        selectors[1] = vaultHandler.withdraw.selector;
        selectors[2] = vaultHandler.mint.selector;
        selectors[3] = vaultHandler.redeem.selector;
        selectors[4] = vaultHandler.reportProfit.selector;
        selectors[5] = vaultHandler.reportLoss.selector;
        selectors[6] = vaultHandler.unreportedLoss.selector;
        selectors[7] = vaultHandler.approve.selector;
        selectors[8] = vaultHandler.transfer.selector;
        selectors[9] = vaultHandler.transferFrom.selector;
        selectors[10] = vaultHandler.increaseTime.selector;
        selectors[11] = vaultHandler.updateDebt.selector;
    }
}
