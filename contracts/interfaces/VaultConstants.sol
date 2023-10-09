// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.18;

// prettier-ignore
contract Roles {
    uint256 public constant ADD_STRATEGY_MANAGER        = 1;
    uint256 public constant REVOKE_STRATEGY_MANAGER     = 2;
    uint256 public constant FORCE_REVOKE_MANAGER        = 4;
    uint256 public constant ACCOUNTANT_MANAGER          = 8;
    uint256 public constant QUEUE_MANAGER              = 16;
    uint256 public constant REPORTING_MANAGER          = 32;
    uint256 public constant DEBT_MANAGER               = 64;
    uint256 public constant MAX_DEBT_MANAGER          = 128;
    uint256 public constant DEPOSIT_LIMIT_MANAGER     = 256;
    uint256 public constant WITHDRAW_LIMIT_MANAGER    = 512;
    uint256 public constant MINIMUM_IDLE_MANAGER     = 1024;
    uint256 public constant PROFIT_UNLOCK_MANAGER    = 2048;
    uint256 public constant DEBT_PURCHASER           = 4096;
    uint256 public constant EMERGENCY_MANAGER        = 8192;
    uint256 public constant ALL                     = 16383;
}

contract VaultConstants is Roles {
    uint256 public constant MAX_QUEUE = 10;

    uint256 public constant MAX_BPS = 10_000;

    uint256 public constant MAX_BPS_EXTENDED = 1_000_000_000_000;

    uint256 public constant STRATEGY_ADDED = 1;
    uint256 public constant STRATEGY_REVOKED = 2;

    uint256 public constant ROLE_OPENED = 1;
    uint256 public constant ROLE_CLOSED = 2;
}
