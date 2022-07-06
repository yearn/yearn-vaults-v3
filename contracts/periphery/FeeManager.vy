# @version 0.3.4

from vyper.interfaces import ERC20

# INTERFACES #
struct StrategyParams:
    activation: uint256
    lastReport: uint256
    currentDebt: uint256
    maxDebt: uint256
    totalGain: uint256
    totalLoss: uint256

interface IVault:
    def strategies(strategy: address) -> StrategyParams: view

interface IStrategy:
    def delegatedAssets() -> uint256: view

# EVENTS #
event CommitFeeManager:
    feeManager: address

event ApplyFeeManager:
    feeManager: address

event UpdatePerformanceFee:
    performanceFee: uint256

event UpdateManagementFee:
    managementFee: uint256

event DistributeRewards:
    rewards: uint256


# STRUCTS #
struct Fee:
    managementFee: uint256
    performanceFee: uint256


# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000
MAX_SHARE: constant(uint256) = 7_500
# NOTE: A four-century period will be missing 3 of its 100 Julian leap years, leaving 97.
#       So the average year has 365 + 97/400 = 365.2425 days
#       ERROR(Julian): -0.0078
#       ERROR(Gregorian): -0.0003
#       A day = 24 * 60 * 60 sec = 86400 sec
#       365.2425 * 86400 = 31556952.0
SECS_PER_YEAR: constant(uint256) = 31_556_952  # 365.2425 days


# STORAGE #
feeManager: public(address)
futureFeeManager: public(address)
fees: public(HashMap[address, Fee])


@external
def __init__():
    self.feeManager = msg.sender


@view
@external
def assessFees(strategy: address, gain: uint256) -> uint256:
    """
    @dev assumes gain > 0
    """
    strategyParams: StrategyParams = IVault(msg.sender).strategies(strategy)
    fee: Fee = self.fees[strategy]
    duration: uint256 = block.timestamp - strategyParams.lastReport

    managementFee: uint256 = (
        ((strategyParams.currentDebt - IStrategy(strategy).delegatedAssets()))
        * duration
        * fee.managementFee
        / MAX_BPS
        / SECS_PER_YEAR
    )
    performanceFee: uint256 = (gain * fee.performanceFee) / MAX_BPS
    totalFee: uint256 = managementFee + performanceFee

    # ensure fee does not exceed more than 75% of gain
    maximumFee: uint256 = (gain * MAX_SHARE) / MAX_BPS
    # test with min?
    if totalFee > maximumFee:
        totalFee = maximumFee

    return totalFee


@external
def distribute(vault: ERC20):
    assert msg.sender == self.feeManager, "not fee manager"
    rewards: uint256 = vault.balanceOf(self)
    vault.transfer(msg.sender, rewards)
    log DistributeRewards(rewards)


@external
def setPerformanceFee(vault: address, performanceFee: uint256):
    assert msg.sender == self.feeManager, "not fee manager"
    assert performanceFee <= self._performanceFeeThreshold(), "exceeds performance fee threshold"
    self.fees[vault].performanceFee = performanceFee
    log UpdatePerformanceFee(performanceFee)


@external
def setManagementFee(vault: address, managementFee: uint256):
    assert msg.sender == self.feeManager, "not fee manager"
    assert managementFee <= self._managementFeeThreshold(), "exceeds management fee threshold"
    self.fees[vault].managementFee = managementFee
    log UpdateManagementFee(managementFee)


@external
def commitFeeManager(futureFeeManager: address):
    assert msg.sender == self.feeManager, "not fee manager"
    self.futureFeeManager = futureFeeManager
    log CommitFeeManager(futureFeeManager)


@external
def applyFeeManager():
    assert msg.sender == self.feeManager, "not fee manager"
    assert self.futureFeeManager != ZERO_ADDRESS, "future fee manager != zero address"
    futureFeeManager: address = self.futureFeeManager
    self.feeManager = futureFeeManager
    log ApplyFeeManager(futureFeeManager)


@view
@external
def performanceFeeThreshold() -> uint256:
    return self._performanceFeeThreshold()


@view
@internal
def _performanceFeeThreshold() -> uint256:
    return MAX_BPS / 2


@view
@external
def managementFeeThreshold() -> uint256:
    return self._managementFeeThreshold()


@view
@internal
def _managementFeeThreshold() -> uint256:
    return MAX_BPS
