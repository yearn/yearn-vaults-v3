// SPDX-License-Identifier: UNLICENSED
pragma solidity >=0.8.18;

import "forge-std/console.sol";
import {Setup} from "./Setup.sol";

abstract contract BaseInvariant is Setup {
    function setUp() public virtual override {
        super.setUp();
    }

    function assert_totalAssets(
        uint256 _totalDeposits,
        uint256 _totalWithdraw,
        uint256 _totalGain,
        uint256 _totalLosses
    ) public {
        assertEq(
            vault.totalAssets(),
            _totalDeposits + _totalGain - _totalWithdraw - _totalLosses
        );
        assertEq(vault.totalAssets(), vault.totalDebt() + vault.totalIdle());
    }

    function assert_maxWithdraw(bool unreportedLoss) public {
        if (unreportedLoss) {
            // withdraw would revert with unreported loss so maxWithdraw is totalIdle
            assertLe(vault.maxWithdraw(msg.sender), vault.totalIdle());
        } else {
            assertLe(vault.maxWithdraw(msg.sender), vault.totalAssets());
        }
        assertLe(vault.maxWithdraw(msg.sender, 10_000), vault.totalAssets());
    }

    function assert_maxRedeem(bool unreportedLoss) public {
        assertLe(vault.maxRedeem(msg.sender), vault.totalSupply());
        assertLe(vault.maxRedeem(msg.sender), vault.balanceOf(msg.sender));
        if (unreportedLoss) {
            assertLe(vault.maxRedeem(msg.sender, 0), vault.totalIdle());
        } else {
            assertLe(vault.maxRedeem(msg.sender, 0), vault.totalSupply());
            assertLe(
                vault.maxRedeem(msg.sender, 0),
                vault.balanceOf(msg.sender)
            );
        }
    }

    function assert_maxRedeemEqualsMaxWithdraw(bool unreportedLoss) public {
        if (unreportedLoss) {
            assertApproxEq(
                vault.maxWithdraw(msg.sender, 10_000),
                vault.convertToAssets(vault.maxRedeem(msg.sender)),
                3
            );
            assertApproxEq(
                vault.maxRedeem(msg.sender),
                vault.convertToShares(vault.maxWithdraw(msg.sender, 10_000)),
                3
            );
        } else {
            assertApproxEq(
                vault.maxWithdraw(msg.sender),
                vault.convertToAssets(vault.maxRedeem(msg.sender)),
                3
            );
            assertApproxEq(
                vault.maxRedeem(msg.sender),
                vault.convertToShares(vault.maxWithdraw(msg.sender)),
                3
            );
        }
    }

    function assert_unlockingTime() public {
        uint256 unlockingDate = vault.fullProfitUnlockDate();
        uint256 balance = vault.balanceOf(address(vault));
        uint256 unlockedShares = vault.unlockedShares();
        if (unlockingDate != 0 && vault.profitUnlockingRate() > 0) {
            if (
                block.timestamp ==
                vault.strategies(address(strategy)).last_report
            ) {
                assertEq(unlockedShares, 0);
                assertGt(balance, 0);
            } else if (block.timestamp < unlockingDate) {
                assertGt(unlockedShares, 0);
                assertGt(balance, 0);
            } else {
                // We should have unlocked full balance
                assertEq(balance, 0);
                assertGt(unlockedShares, 0);
            }
        } else {
            assertEq(balance, 0);
        }
    }

    function assert_unlockedShares() public {
        uint256 unlockedShares = vault.unlockedShares();
        uint256 fullBalance = vault.balanceOf(address(vault)) + unlockedShares;
        uint256 unlockingDate = vault.fullProfitUnlockDate();
        if (
            unlockingDate != 0 &&
            vault.profitUnlockingRate() > 0 &&
            block.timestamp < unlockingDate
        ) {
            assertLt(unlockedShares, fullBalance);
        } else {
            assertEq(unlockedShares, fullBalance);
            assertEq(vault.balanceOf(address(vault)), 0);
        }
    }

    function assert_previewMintAndConvertToAssets() public {
        assertApproxEq(vault.previewMint(WAD), vault.convertToAssets(WAD), 1);
    }

    function assert_previewWithdrawAndConvertToShares() public {
        assertApproxEq(
            vault.previewWithdraw(WAD),
            vault.convertToShares(WAD),
            1
        );
    }

    function assert_balanceAndTotalAssets(bool unreported) public {
        if (!unreported) {
            assertLe(
                vault.totalAssets(),
                asset.balanceOf(address(strategy)) +
                    asset.balanceOf(address(vault))
            );
        }
        assertEq(vault.totalIdle(), asset.balanceOf(address(vault)));
    }

    function assert_totalDebt(bool unreported) public {
        uint256 currentDebt = vault.strategies(address(strategy)).current_debt;
        assertEq(vault.totalDebt(), currentDebt);
        if (!unreported) {
            assertGe(asset.balanceOf(address(strategy)), currentDebt);
        }
    }
}
