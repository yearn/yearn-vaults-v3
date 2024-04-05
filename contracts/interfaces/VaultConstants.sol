// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.8.18;

// prettier-ignore
contract VaultConstants {
    uint256 public constant MAX_QUEUE                       = 10;
    uint256 public constant MAX_BPS                     = 10_000;
    uint256 public constant MAX_BPS_EXTENDED = 1_000_000_000_000;
    uint256 public constant STRATEGY_ADDED                   = 1;
    uint256 public constant STRATEGY_REVOKED                 = 2;
}
