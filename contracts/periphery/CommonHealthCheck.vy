# @version 0.3.4

from vyper.interfaces import ERC20

# INTERFACES #
interface IStrategy:
    def vault() -> address: view

# EVENTS #
event CommitHealthCheckManager:
    healthCheckManager: address

event ApplyHealthCheckManager:
    healthCheckManager: address

event DisableHealthCheckStatusUpdated:
    strategy: address
    isDisabled: bool

# STRUCTS #
struct Limits:
    profitLimitRatio: uint256
    lossLimitRatio: uint256
    active: bool


# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000


# STORAGE #
healthCheckManager: public(address)
futureHealthCheckManager: public(address)
strategyLimits: public(HashMap[address, Limits])

profitLimitRatio: public(uint256)
lossLimitRatio: public(uint256)
disabledHealthChecks: public(HashMap[address, bool])


@external
def __init__():
    self.healthCheckManager = msg.sender
    self.profitLimitRatio = 100
    self.lossLimitRatio = 1


@external
def setDefaultProfitLimitRatio(profitLimitRatio: uint256):
    assert msg.sender == self.healthCheckManager, "not health check manager"
    assert profitLimitRatio < MAX_BPS, "profit limit ratio out of bounds"
    self.profitLimitRatio = profitLimitRatio


@external
def setDisabledHealthCheckState(strategy: address, isDisabled: bool):
    # health checks are enabled by default
    assert msg.sender == self.healthCheckManager, "not health check manager"
    log DisableHealthCheckStatusUpdated(strategy, isDisabled)
    self.disabledHealthChecks[strategy] = isDisabled


@external
def setDefaultLossLimitRatio(lossLimitRatio: uint256):
    assert msg.sender == self.healthCheckManager, "not health check manager"
    assert lossLimitRatio < MAX_BPS, "loss limit ratio out of bounds"
    self.lossLimitRatio = lossLimitRatio


@external
def setStrategyLimits(strategy: address, profitLimitRatio: uint256, lossLimitRatio: uint256):
    assert msg.sender == self.healthCheckManager, "not health check manager"
    assert profitLimitRatio < MAX_BPS, "profit limit ratio out of bounds"
    assert lossLimitRatio < MAX_BPS, "loss limit ratio out of bounds"
    self.strategyLimits[strategy] = Limits({
        profitLimitRatio: profitLimitRatio,
        lossLimitRatio: lossLimitRatio,
        active: True
    })


@external
def commitHealthCheckManager(futureHealthCheckManager: address):
    assert msg.sender == self.healthCheckManager, "not health check manager"
    self.futureHealthCheckManager = futureHealthCheckManager
    log CommitHealthCheckManager(futureHealthCheckManager)


@external
def applyHealthCheckManager():
    assert msg.sender == self.healthCheckManager, "not health check manager"
    assert self.futureHealthCheckManager != ZERO_ADDRESS, "future health check manager != zero address"
    futureHealthCheckManager: address = self.futureHealthCheckManager
    self.healthCheckManager = futureHealthCheckManager
    log ApplyHealthCheckManager(futureHealthCheckManager)


@view
@external
def check(strategy: address, gain: uint256, loss: uint256, currentDebt: uint256) -> bool:
    limits: Limits = self.strategyLimits[strategy]
    # use default values if limits have not been set
    profitLimitRatio: uint256 = self.profitLimitRatio
    lossLimitRatio: uint256 = self.lossLimitRatio
    if limits.active:
        profitLimitRatio = limits.profitLimitRatio
        lossLimitRatio = limits.lossLimitRatio

    if (gain > ((currentDebt * profitLimitRatio) / MAX_BPS)):
        return False
    if (loss > ((currentDebt * lossLimitRatio) / MAX_BPS)):
        return False
    return True
