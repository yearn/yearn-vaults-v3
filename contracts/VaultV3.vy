# @version 0.3.4

from vyper.interfaces import ERC20
from vyper.interfaces import ERC20Detailed

# TODO: external contract: factory
# TODO: external contract: access control
# TODO: external contract: fee manager
# TODO: external contract: healtcheck

# INTERFACES #
interface IStrategy:
    def asset() -> address: view
    def vault() -> address: view
    def investable() -> (uint256, uint256): view
    def withdrawable() -> uint256: view
    def freeFunds(amount: uint256) -> uint256: nonpayable
    def totalAssets() -> (uint256): view

interface IFeeManager:
    def assess_fees(strategy: address, gain: uint256) -> uint256: view

# EVENTS #
event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Deposit:
    recipient: indexed(address)
    shares: uint256
    amount: uint256

event Withdraw:
    recipient: indexed(address)
    shares: uint256
    amount: uint256

event StrategyAdded:
    strategy: indexed(address)

event StrategyRevoked:
    strategy: indexed(address)

event StrategyMigrated:
    old_strategy: indexed(address)
    new_strategy: indexed(address)

event StrategyReported:
    strategy: indexed(address)
    gain: uint256
    loss: uint256
    currentDebt: uint256
    totalGain: uint256
    totalLoss: uint256
    totalFees: uint256

event DebtUpdated:
    strategy: address
    currentDebt: uint256
    newDebt: uint256

event UpdateFeeManager:
    feeManager: address

event UpdateDepositLimit:
    depositLimit: uint256

# STRUCTS #
struct StrategyParams:
    activation: uint256
    lastReport: uint256
    currentDebt: uint256
    maxDebt: uint256
    totalGain: uint256
    totalLoss: uint256

# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000


# IMMUTABLE #
ASSET: immutable(ERC20)
DECIMALS: immutable(uint256)

# STORAGE #
strategies: public(HashMap[address, StrategyParams])
balanceOf: public(HashMap[address, uint256])
totalSupply: public(uint256)
totalDebt: public(uint256)
totalIdle: public(uint256)
lastReport: public(uint256)
lockedProfit: public(uint256)
previousHarvestTimeDelta: public(uint256)
depositLimit: public(uint256)

feeManager: public(address)
healthCheck: public(address)


@external
def __init__(asset: ERC20):
    ASSET = asset
    DECIMALS = convert(ERC20Detailed(asset.address).decimals(), uint256)


# SUPPORT FUNCTIONS #

@view
@external
def asset() -> ERC20:
    return ASSET
@view
@external
def decimals() -> uint256:
    return DECIMALS

@view
@internal
def _totalAssets() -> uint256:
    return self.totalIdle + self.totalDebt


@internal
def _burnShares(shares: uint256, owner: address):
    # TODO: do we need to check?
    self.balanceOf[owner] -= shares
    self.totalSupply -= shares


@internal
def _calculateLockedProfit() -> uint256:
    """
    @notice
        Returns time adjusted locked profits depending on the current time delta and
        the previous harvest time delta.
    @return The time adjusted locked profits due to pps increase spread
    """
    currentTimeDelta: uint256 = block.timestamp - self.lastReport

    if currentTimeDelta < self.previousHarvestTimeDelta:
        return self.lockedProfit - ((self.lockedProfit * currentTimeDelta) / self.previousHarvestTimeDelta)
    return 0


@internal
def _updateReportTimestamps():
    """
    maintains longer (fairer) harvest periods on close timed harvests
    NOTE: correctly adjust time delta to avoid reducing locked-until time
          all following examples have previousHarvestTimeDelta = 10 set at h2 and used on h3
          if new time delta reduces previous locked-until, keep locked-until and adjust remaining time
          h1 = t0, h2 = t10 and h3 = t13 =>
              currentTimeDelta = 3, (new)previousHarvestTimeDelta = 7 (10-3), locked until t20
          h1 = t0, h2 = t10 and h3 = t14 =>
              currentTimeDelta = 4, (new)previousHarvestTimeDelta = 6 (10-4), locked until t20
          on 2nd example: h2 is getting carried into h3 (minus time delta 4) since it was previously trying to reach t20.
          so it continues to spread the lock up to that point, and thus avoids reducing the previous distribution time.

          if locked-until is unchanged, to avoid extra storage read and subtraction cost [behaves as examples below]
          h1 = t0, h2 = t10 and h3 = t15 =>
              currentTimeDelta = 5, (new)previousHarvestTimeDelta = 5 locked until t20

          if next total time delta is higher than previous period remaining, locked-until will increase
          h1 = t0, h2 = t10 and h3 = t16 =>
              currentTimeDelta = 6, (new)previousHarvestTimeDelta = 6 locked until t22
          h1 = t0, h2 = t10 and h3 = t17 =>
              currentTimeDelta = 7, (new)previousHarvestTimeDelta = 7 locked until t24

          currentTimeDelta is the time delta between now and lastReport.
          previousHarvestTimeDelta is the time delta between lastReport and the previous lastReport
          previousHarvestTimeDelta is assigned the higher value between currentTimeDelta and (previousHarvestTimeDelta - currentTimeDelta)
    """

    # TODO: check how to solve deposit sniping for very profitable and infrequent strategy reports
    # when there are also other more frequent strategies reducing time delta.
    # (need to add time delta per strategy + accumulator)
    currentTimeDelta: uint256 = block.timestamp - self.lastReport
    if self.previousHarvestTimeDelta > currentTimeDelta * 2:
      self.previousHarvestTimeDelta = self.previousHarvestTimeDelta - currentTimeDelta
    else:
      self.previousHarvestTimeDelta = currentTimeDelta
    self.lastReport = block.timestamp


@view
@internal
def _amountForShares(shares: uint256) -> uint256:
    _totalSupply: uint256 = self.totalSupply
    amount: uint256 = shares
    if _totalSupply > 0:
        amount = shares * self._totalAssets() / self.totalSupply
    return amount


@internal
def _sharesForAmount(amount: uint256) -> uint256:
    _totalSupply: uint256 = self.totalSupply
    shares: uint256 = amount
    if _totalSupply > 0:
        shares = amount * _totalSupply / self._totalAssets()
    return shares


@internal
def _issueSharesForAmount(amount: uint256, recipient: address) -> uint256:
    newShares: uint256 = self._sharesForAmount(amount)

    assert newShares > 0

    self.balanceOf[recipient] += newShares
    self.totalSupply += newShares

    # TODO: emit event
    return newShares


@internal
def erc20_safe_transferFrom(token: address, sender: address, receiver: address, amount: uint256):
    # Used only to send tokens that are not the type managed by this Vault.
    # HACK: Used to handle non-compliant tokens like USDT
    response: Bytes[32] = raw_call(
        token,
        concat(
            method_id("transferFrom(address,address,uint256)"),
            convert(sender, bytes32),
            convert(receiver, bytes32),
            convert(amount, bytes32),
        ),
        max_outsize=32,
    )
    if len(response) > 0:
        assert convert(response, bool), "Transfer failed!"


@internal
def erc20_safe_transfer(token: address, receiver: address, amount: uint256):
    # Used only to send tokens that are not the type managed by this Vault.
    # HACK: Used to handle non-compliant tokens like USDT
    response: Bytes[32] = raw_call(
        token,
        concat(
            method_id("transfer(address,uint256)"),
            convert(receiver, bytes32),
            convert(amount, bytes32),
        ),
        max_outsize=32,
    )
    if len(response) > 0:
        assert convert(response, bool), "Transfer failed!"


# USER FACING FUNCTIONS #
@external
def deposit(_amount: uint256, _recipient: address) -> uint256:
    assert _recipient not in [self, ZERO_ADDRESS], "invalid recipient"
    amount: uint256 = _amount

    if amount == MAX_UINT256:
        amount = ASSET.balanceOf(msg.sender)

    assert self._totalAssets() + amount <= self.depositLimit, "exceed deposit limit"
    assert amount > 0, "cannot deposit zero"

    shares: uint256 = self._issueSharesForAmount(amount, _recipient)

    self.erc20_safe_transferFrom(ASSET.address, msg.sender, self, amount)
    self.totalIdle += amount

    log Deposit(_recipient, shares, amount)

    return shares


@external
def withdraw(_shares: uint256, _recipient: address, _strategies: DynArray[address, 10]) -> uint256:
    # TODO: allow withdrawals by approved ?
    owner: address = msg.sender
    shares: uint256 = _shares
    sharesBalance: uint256 = self.balanceOf[owner]

    if _shares == MAX_UINT256:
        shares = sharesBalance

    assert sharesBalance >= shares, "insufficient shares to withdraw"
    assert shares > 0, "no shares to withdraw"

    amount: uint256 = self._amountForShares(shares)

    # TODO: withdraw from strategies

    assert self.totalIdle >= amount, "insufficient total idle"

    self._burnShares(shares, owner)
    self.totalIdle -= amount

    self.erc20_safe_transfer(ASSET.address, _recipient, amount)

    log Withdraw(_recipient, shares, amount)

    return amount


# SHARE MANAGEMENT FUNCTIONS #
@view
@external
def totalAssets() -> uint256:
    return self._totalAssets()


@view
@external
def pricePerShare() -> uint256:
    return self._amountForShares(10 ** DECIMALS)


@external
def sharesForAmount(amount: uint256) -> uint256:
    return self._sharesForAmount(amount)


@external
def amountForShares(shares: uint256) -> uint256:
    return self._amountForShares(shares)


@view
@external
def availableDepositLimit() -> uint256:
    if self.depositLimit > self._totalAssets():
        return self.depositLimit - self._totalAssets()
    return 0


# STRATEGY MANAGEMENT FUNCTIONS #
@external
def addStrategy(new_strategy: address):
    # TODO: permissioned: STRATEGY_MANAGER
    assert new_strategy != ZERO_ADDRESS, "strategy cannot be zero address"
    assert IStrategy(new_strategy).asset() == ASSET.address, "invalid asset"
    assert IStrategy(new_strategy).vault() == self, "invalid vault"
    assert self.strategies[new_strategy].activation == 0, "strategy already active"

    self.strategies[new_strategy] = StrategyParams({
        activation: block.timestamp,
        lastReport: block.timestamp,
        currentDebt: 0,
        maxDebt: 0,
        totalGain: 0,
        totalLoss: 0
    })

    log StrategyAdded(new_strategy)


@internal
def _revokeStrategy(old_strategy: address):
    # TODO: permissioned: STRATEGY_MANAGER
    assert self.strategies[old_strategy].activation != 0, "strategy not active"
    # NOTE: strategy needs to have 0 debt to be revoked
    assert self.strategies[old_strategy].currentDebt == 0, "strategy has debt"

    # NOTE: strategy params are set to 0 (warning: it can be readded)
    self.strategies[old_strategy] = StrategyParams({
        activation: 0,
        lastReport: 0,
        currentDebt: 0,
        maxDebt: 0,
        totalGain: 0,
        totalLoss: 0
    })

    log StrategyRevoked(old_strategy)


@external
def revokeStrategy(old_strategy: address):
    self._revokeStrategy(old_strategy)


@external
def migrateStrategy(new_strategy: address, old_strategy: address):
    # TODO: permissioned: STRATEGY_MANAGER

    assert self.strategies[old_strategy].activation != 0, "old strategy not active"
    assert self.strategies[old_strategy].currentDebt == 0, "old strategy has debt"
    assert new_strategy != ZERO_ADDRESS, "strategy cannot be zero address"
    assert IStrategy(new_strategy).asset() == ASSET.address, "invalid asset"
    assert IStrategy(new_strategy).vault() == self, "invalid vault"
    assert self.strategies[new_strategy].activation == 0, "strategy already active"

    migrated_strategy: StrategyParams = self.strategies[old_strategy]

    # NOTE: we add strategy with same params than the strategy being migrated
    self.strategies[new_strategy] = StrategyParams({
       activation: block.timestamp,
       lastReport: block.timestamp,
       currentDebt: migrated_strategy.currentDebt,
       maxDebt: migrated_strategy.maxDebt,
       totalGain: 0,
       totalLoss: 0
    })

    self._revokeStrategy(old_strategy)

    log StrategyMigrated(old_strategy, new_strategy)


@external
def updateMaxDebtForStrategy(strategy: address, new_maxDebt: uint256):
    # TODO: permissioned: DEBT_MANAGER
    assert self.strategies[strategy].activation != 0, "inactive strategy"
    # TODO: should we check that totalMaxDebt is not over 100% of assets?
    self.strategies[strategy].maxDebt = new_maxDebt
    # TODO: should this emit an event?


@external
def updateDebt(strategy: address) -> uint256:
    # TODO: permissioned: DEBT_MANAGER (or maybe open?)
    # TODO: rebalance debt. if the strategy is allowed to take more debt and the strategy wants that debt, the vault will send more. if the strategy has too much debt, the vault will have less
    currentDebt: uint256 = self.strategies[strategy].currentDebt

    minDesiredDebt: uint256 = 0
    maxDesiredDebt: uint256 = 0
    minDesiredDebt, maxDesiredDebt = IStrategy(strategy).investable()

    newDebt: uint256 = self.strategies[strategy].maxDebt

    if newDebt > currentDebt:
        # only check if debt is increasing
        # if debt is decreasing, we ignore strategy min debt
        assert (newDebt >= minDesiredDebt), "new debt less than min debt"

    if newDebt > maxDesiredDebt:
        newDebt = maxDesiredDebt

    assert newDebt != currentDebt, "new debt equals current debt"

    if currentDebt > newDebt:
        # reduce debt
        amountToWithdraw: uint256 = currentDebt - newDebt
        withdrawable: uint256 = IStrategy(strategy).withdrawable()
        assert withdrawable != 0, "nothing to withdraw"

        # if insufficient withdrawable, withdraw what we can
        if (withdrawable < amountToWithdraw):
            amountToWithdraw = withdrawable
            newDebt = currentDebt - withdrawable

        IStrategy(strategy).freeFunds(amountToWithdraw)
        ASSET.transferFrom(strategy, self, amountToWithdraw)
        self.totalIdle += amountToWithdraw
        self.totalDebt -= amountToWithdraw
    else:
        # increase debt
        amountToTransfer: uint256 = newDebt - currentDebt
        # if insufficient funds to deposit, transfer only what is free
        if amountToTransfer > self.totalIdle:
            amountToTransfer = self.totalIdle
            newDebt = currentDebt + amountToTransfer
        ASSET.transfer(strategy, amountToTransfer)
        self.totalIdle -= amountToTransfer
        self.totalDebt += amountToTransfer

    self.strategies[strategy].currentDebt = newDebt

    log DebtUpdated(strategy, currentDebt, newDebt)
    return newDebt

# # P&L MANAGEMENT FUNCTIONS #
@external
def processReport(strategy: address) -> (uint256, uint256):
    # TODO: permissioned: ACCOUNTING_MANAGER (open?)

    assert self.strategies[strategy].activation != 0, "inactive strategy"
    totalAssets: uint256 = IStrategy(strategy).totalAssets()
    currentDebt: uint256 = self.strategies[strategy].currentDebt
    assert totalAssets != currentDebt, "nothing to report"

    gain: uint256 = 0
    loss: uint256 = 0

    # TODO: implement health check

    if totalAssets > currentDebt:
        gain = totalAssets - currentDebt
    else:
        loss = currentDebt - totalAssets

    if loss > 0:
        self.strategies[strategy].totalLoss += loss
        self.strategies[strategy].currentDebt -= loss

        lockedProfitBeforeLoss: uint256 = self._calculateLockedProfit()
        if lockedProfitBeforeLoss > loss:
            self.lockedProfit = lockedProfitBeforeLoss - loss
        else:
            self.lockedProfit = 0

    totalFees: uint256 = 0
    if gain > 0:
        feeManager: address = self.feeManager
        # if fee manager is not set, fees are zero
        if feeManager != ZERO_ADDRESS:
            totalFees = IFeeManager(feeManager).assess_fees(strategy, gain)
            # if fees are non-zero, issue shares
            if totalFees > 0:
                self._issueSharesForAmount(totalFees, feeManager)

        # gains are always realized pnl (i.e. not upnl)
        self.strategies[strategy].totalGain += gain
        # update current debt after processing management fee
        self.strategies[strategy].currentDebt += gain
        self.lockedProfit = self._calculateLockedProfit() + gain - totalFees

    self.strategies[strategy].lastReport = block.timestamp
    self._updateReportTimestamps()

    strategyParams: StrategyParams = self.strategies[strategy]
    log StrategyReported(
        strategy,
        gain,
        loss,
        strategyParams.currentDebt,
        strategyParams.totalGain,
        strategyParams.totalLoss,
        totalFees
    )
    return (gain, loss)


# SETTERS #
@external
def setFeeManager(newFeeManager: address):
    # TODO: permissioning
    self.feeManager = newFeeManager
    log UpdateFeeManager(newFeeManager)


@external
def setDepositLimit(depositLimit: uint256):
    # TODO: permissioning
    self.depositLimit = depositLimit
    log UpdateDepositLimit(depositLimit)


@internal
def _transfer(sender: address, receiver: address, amount: uint256):
    # See note on `transfer()`.

    # Protect people from accidentally sending their shares to bad places
    assert receiver not in [self, ZERO_ADDRESS]
    self.balanceOf[sender] -= amount
    self.balanceOf[receiver] += amount
    log Transfer(sender, receiver, amount)


@external
def transfer(receiver: address, amount: uint256) -> bool:
    self._transfer(msg.sender, receiver, amount)
    return True


# def forceProcessReport(strategy: address):
#     # permissioned: ACCOUNTING_MANAGER
#     # TODO: allows processing the report with losses ! this should only be called in special situations
#     #    - deactivate the healthcheck
#     #    - call process report
#     return

# # DEBT MANAGEMENT FUNCTIONS #
# def setMaxDebtForStrategy(strategy: address, maxAmount: uint256):
#     # permissioned: DEBT_MANAGER
#     # TODO: change maxDebt in strategy params for _strategy
#     return


# def updateDebtEmergency():
#     # permissioned: EMERGENCY_DEBT_MANAGER
#     # TODO: use a different function to rebalance the debt. this function allows to incur into losses while withdrawing
#     # this function needs to be called through private mempool as could have MEV
#     return


# # EMERGENCY FUNCTIONS #
# def setEmergencyShutdown(emergency: bool):
#     # permissioned: EMERGENCY_MANAGER
#     # TODO: change emergency shutdown flag
#     return

# # SETTERS #
# def setHealthcheck(newhealtcheck: address):
#     # permissioned: SETTER
#     # TODO: change healtcheck contract
#     return
