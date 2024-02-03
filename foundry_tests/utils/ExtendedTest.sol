// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.18;

import {Test} from "forge-std/Test.sol";

contract ExtendedTest is Test {
    // solhint-disable-next-line
    function assertNeq(address a, address b) internal {
        if (a == b) {
            emit log("Error: a != b not satisfied [address]");
            emit log_named_address("  Expected", b);
            emit log_named_address("    Actual", a);
            fail();
        }
    }

    // @dev checks whether @a is within certain percentage of @b
    // @a actual value
    // @b expected value
    // solhint-disable-next-line
    function assertRelApproxEq(
        uint256 a,
        uint256 b,
        uint256 maxPercentDelta
    ) internal virtual {
        uint256 delta = a > b ? a - b : b - a;
        uint256 maxRelDelta = b / maxPercentDelta;

        if (delta > maxRelDelta) {
            emit log("Error: a ~= b not satisfied [uint]");
            emit log_named_uint("  Expected", b);
            emit log_named_uint("    Actual", a);
            emit log_named_uint(" Max Delta", maxRelDelta);
            emit log_named_uint("     Delta", delta);
            fail();
        }
    }

    // Can be removed once https://github.com/dapphub/ds-test/pull/25 is merged and we update submodules, but useful for now
    // solhint-disable-next-line
    function assertApproxEq(
        uint256 a,
        uint256 b,
        uint256 margin_of_error
    ) internal {
        if (a > b) {
            if (a - b > margin_of_error) {
                emit log("Error a not equal to b");
                emit log_named_uint("  Expected", b);
                emit log_named_uint("    Actual", a);
                fail();
            }
        } else {
            if (b - a > margin_of_error) {
                emit log("Error a not equal to b");
                emit log_named_uint("  Expected", b);
                emit log_named_uint("    Actual", a);
                fail();
            }
        }
    }

    // solhint-disable-next-line
    function assertApproxEq(
        uint256 a,
        uint256 b,
        uint256 margin_of_error,
        string memory err
    ) internal {
        if (a > b) {
            if (a - b > margin_of_error) {
                emit log_named_string("Error", err);
                emit log_named_uint("  Expected", b);
                emit log_named_uint("    Actual", a);
                fail();
            }
        } else {
            if (b - a > margin_of_error) {
                emit log_named_string("Error", err);
                emit log_named_uint("  Expected", b);
                emit log_named_uint("    Actual", a);
                fail();
            }
        }
    }
}
