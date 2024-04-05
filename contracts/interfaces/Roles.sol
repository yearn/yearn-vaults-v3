// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.8.18;

// prettier-ignore
library Roles {
    uint256 internal constant ADD_STRATEGY_MANAGER             = 1;
    uint256 internal constant REVOKE_STRATEGY_MANAGER          = 2;
    uint256 internal constant FORCE_REVOKE_MANAGER             = 4;
    uint256 internal constant ACCOUNTANT_MANAGER               = 8;
    uint256 internal constant QUEUE_MANAGER                   = 16;
    uint256 internal constant REPORTING_MANAGER               = 32;
    uint256 internal constant DEBT_MANAGER                    = 64;
    uint256 internal constant MAX_DEBT_MANAGER               = 128;
    uint256 internal constant DEPOSIT_LIMIT_MANAGER          = 256;
    uint256 internal constant WITHDRAW_LIMIT_MANAGER         = 512;
    uint256 internal constant MINIMUM_IDLE_MANAGER          = 1024;
    uint256 internal constant PROFIT_UNLOCK_MANAGER         = 2048;
    uint256 internal constant DEBT_PURCHASER                = 4096;
    uint256 internal constant EMERGENCY_MANAGER             = 8192;
    uint256 internal constant ALL                          = 16383;
}
