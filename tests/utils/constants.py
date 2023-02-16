from enum import IntFlag

DAY = 86400
WEEK = 7 * DAY
YEAR = 31_556_952  # same value used in vault
MAX_INT = 2**256 - 1
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
MAX_BPS = 1_000_000_000_000
MAX_BPS_ACCOUNTANT = 10_000


class ROLES(IntFlag):
    STRATEGY_MANAGER = 1
    DEBT_MANAGER = 2
    REPORTING_MANAGER = 4
    ACCOUNTING_MANAGER = 8
    SET_ACCOUNTANT_MANAGER = 16
    SWEEPER = 32
    EMERGENCY_MANAGER = 64
    KEEPER = 128
