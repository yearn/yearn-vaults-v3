# @version 0.3.4

# FeeManager without any fee threshold

from vyper.interfaces import ERC20

# INTERFACES #
struct StrategyParams:
    activation: uint256
    last_report: uint256
    current_debt: uint256
    max_debt: uint256

interface IVault:
    def strategies(strategy: address) -> StrategyParams: view

interface IStrategy:
    def delegatedAssets() -> uint256: view

# EVENTS #
event CommitFeeManager:
    fee_manager: address

event ApplyFeeManager:
    fee_manager: address

event UpdatePerformanceFee:
    performance_fee: uint256

event UpdateManagementFee:
    management_fee: uint256

event DistributeRewards:
    rewards: uint256


# STRUCTS #
struct Fee:
    management_fee: uint256
    performance_fee: uint256


# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000
# NOTE: A four-century period will be missing 3 of its 100 Julian leap years, leaving 97.
#       So the average year has 365 + 97/400 = 365.2425 days
#       ERROR(Julian): -0.0078
#       ERROR(Gregorian): -0.0003
#       A day = 24 * 60 * 60 sec = 86400 sec
#       365.2425 * 86400 = 31556952.0
SECS_PER_YEAR: constant(uint256) = 31_556_952  # 365.2425 days


# STORAGE #
fee_manager: public(address)
future_fee_manager: public(address)
fees: public(HashMap[address, Fee])


@external
def __init__():
    self.fee_manager = msg.sender


@view
@external
def assess_fees(strategy: address, gain: uint256) -> uint256:
    """
    @dev assumes gain > 0
    """
    strategy_params: StrategyParams = IVault(msg.sender).strategies(strategy)
    fee: Fee = self.fees[strategy]
    duration: uint256 = block.timestamp - strategy_params.last_report

    management_fee: uint256 = (
        ((strategy_params.current_debt - IStrategy(strategy).delegatedAssets()))
        * duration
        * fee.management_fee
        / MAX_BPS
        / SECS_PER_YEAR
    )
    performance_fee: uint256 = (gain * fee.performance_fee) / MAX_BPS
    total_fee: uint256 = management_fee + performance_fee

    return total_fee


@external
def distribute(vault: ERC20):
    assert msg.sender == self.fee_manager, "not fee manager"
    rewards: uint256 = vault.balanceOf(self)
    vault.transfer(msg.sender, rewards)
    log DistributeRewards(rewards)


@external
def set_performance_fee(vault: address, performance_fee: uint256):
    assert msg.sender == self.fee_manager, "not fee manager"
    self.fees[vault].performance_fee = performance_fee
    log UpdatePerformanceFee(performance_fee)


@external
def set_management_fee(vault: address, management_fee: uint256):
    assert msg.sender == self.fee_manager, "not fee manager"
    self.fees[vault].management_fee = management_fee
    log UpdateManagementFee(management_fee)


@external
def commit_fee_manager(future_fee_manager: address):
    assert msg.sender == self.fee_manager, "not fee manager"
    self.future_fee_manager = future_fee_manager
    log CommitFeeManager(future_fee_manager)


@external
def apply_fee_manager():
    assert msg.sender == self.fee_manager, "not fee manager"
    assert self.future_fee_manager != ZERO_ADDRESS, "future fee manager != zero address"
    future_fee_manager: address = self.future_fee_manager
    self.fee_manager = future_fee_manager
    log ApplyFeeManager(future_fee_manager)
