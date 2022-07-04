# @version 0.3.4

from vyper.interfaces import ERC20
from vyper.interfaces import ERC20Detailed

# TODO: external contract: factory
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
event Deposit:
    sender: indexed(address)
    owner: indexed(address)
    assets: uint256
    shares: uint256

event Withdraw:
    sender: indexed(address)
    receiver: indexed(address)
    owner: indexed(address)
    assets: uint256
    shares: uint256

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

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

event UpdatedMaxDebtForStrategy:
    sender: address
    strategy: address
    newDebt: uint256

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

# ENUMS #
enum Roles:
    STRATEGY_MANAGER
    DEBT_MANAGER

# IMMUTABLE #
ASSET: immutable(ERC20)
DECIMALS: immutable(uint256)

# STORAGE #
strategies: public(HashMap[address, StrategyParams])
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])

totalSupply: public(uint256)
totalDebt: public(uint256)
totalIdle: public(uint256)
roles: public(HashMap[address, Roles])
lastReport: public(uint256)
lockedProfit: public(uint256)
previousHarvestTimeDelta: public(uint256)
depositLimit: public(uint256)

feeManager: public(address)
healthCheck: public(address)
role_manager: public(address)
future_role_manager: public(address)

name: public(String[64])
symbol: public(String[32])

# `nonces` track `permit` approvals with signature.
nonces: public(HashMap[address, uint256])
DOMAIN_SEPARATOR: public(bytes32)
DOMAIN_TYPE_HASH: constant(bytes32) = keccak256('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
PERMIT_TYPE_HASH: constant(bytes32) = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)")

@external
def __init__(asset: ERC20, role_manager: address):
    ASSET = asset
    DECIMALS = convert(ERC20Detailed(asset.address).decimals(), uint256)
    self.role_manager = role_manager

## ERC20 ##
@internal
def _spendAllowance(owner: address, sender: address, amount: uint256):
   self.allowance[owner][sender] -= amount

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

@external
def transferFrom(sender: address, receiver: address, amount: uint256) -> bool:
    # Unlimited approval (saves an SSTORE)
    if (self.allowance[sender][msg.sender] < MAX_UINT256):
        allowance: uint256 = self.allowance[sender][msg.sender] - amount
        self.allowance[sender][msg.sender] = allowance
        # NOTE: Allows log filters to have a full accounting of allowance changes
        log Approval(sender, msg.sender, allowance)
    self._transfer(sender, receiver, amount)
    return True

@external
def approve(spender: address, amount: uint256) -> bool:
    self.allowance[msg.sender][spender] = amount
    log Approval(msg.sender, spender, amount)
    return True

@external
def increaseAllowance(spender: address, amount: uint256) -> bool:
    self.allowance[msg.sender][spender] += amount
    log Approval(msg.sender, spender, self.allowance[msg.sender][spender])
    return True

@external
def decreaseAllowance(spender: address, amount: uint256) -> bool:
    self.allowance[msg.sender][spender] -= amount
    log Approval(msg.sender, spender, self.allowance[msg.sender][spender])
    return True

@external
def permit(owner: address, spender: address, amount: uint256, expiry: uint256, signature: Bytes[65]) -> bool:
    assert owner != ZERO_ADDRESS  # dev: invalid owner
    assert expiry == 0 or expiry >= block.timestamp  # dev: permit expired
    nonce: uint256 = self.nonces[owner]
    digest: bytes32 = keccak256(
        concat(
            b'\x19\x01',
            self.DOMAIN_SEPARATOR,
            keccak256(
                concat(
                    PERMIT_TYPE_HASH,
                    convert(owner, bytes32),
                    convert(spender, bytes32),
                    convert(amount, bytes32),
                    convert(nonce, bytes32),
                    convert(expiry, bytes32),
                )
            )
        )
    )
    # NOTE: signature is packed as r, s, v
    r: uint256 = convert(slice(signature, 0, 32), uint256)
    s: uint256 = convert(slice(signature, 32, 32), uint256)
    v: uint256 = convert(slice(signature, 64, 1), uint256)
    assert ecrecover(digest, v, r, s) == owner  # dev: invalid signature
    self.allowance[owner][spender] = amount
    self.nonces[owner] = nonce + 1
    log Approval(owner, spender, amount)
    return True


# SUPPORT FUNCTIONS #
@view
@external
def asset() -> address:
    return ASSET.address

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
def _convertToAssets(shares: uint256) -> uint256:
    _totalSupply: uint256 = self.totalSupply
    amount: uint256 = shares
    if _totalSupply > 0:
        amount = shares * self._totalAssets() / self.totalSupply
    return amount

@view
@internal
def _convertToShares(amount: uint256) -> uint256:
    _totalSupply: uint256 = self.totalSupply
    shares: uint256 = amount
    if _totalSupply > 0:
        shares = amount * _totalSupply / self._totalAssets()
    return shares


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

@internal
def _issueSharesForAmount(amount: uint256, recipient: address) -> uint256:
    newShares: uint256 = self._convertToShares(amount)
    assert newShares > 0

    self.balanceOf[recipient] += newShares
    self.totalSupply += newShares

    # TODO: emit event
    return newShares

@internal
def _deposit(_sender: address, _recipient: address, _assets: uint256) -> uint256:
    assert _recipient not in [self, ZERO_ADDRESS], "invalid recipient"
    assets: uint256 = _assets

    if assets == MAX_UINT256:
        assets = ASSET.balanceOf(_sender)

    assert self._totalAssets() + assets <= self.depositLimit, "exceed deposit limit"
    assert assets > 0, "cannot deposit zero"

    shares: uint256 = self._issueSharesForAmount(_assets, _recipient)

    self.erc20_safe_transferFrom(ASSET.address, msg.sender, self, _assets)
    self.totalIdle += _assets

    log Deposit(_sender, _recipient, _assets, shares)

    return shares

@internal
def _redeem(_sender: address, _receiver: address, _owner: address, _shares: uint256, _strategies: DynArray[address, 10] = []) -> uint256:
    if _sender != _owner:
      self._spendAllowance(_owner, _sender, _shares)

    shares: uint256 = _shares
    sharesBalance: uint256 = self.balanceOf[_owner]

    if _shares == MAX_UINT256:
        shares = sharesBalance

    # TODO: is this needed? will revert in burn call
    assert sharesBalance >= shares, "insufficient shares to withdraw"
    assert shares > 0, "no shares to withdraw"

    assets: uint256 = self._convertToAssets(_shares)

    if assets > self.totalIdle:
        # load to memory to save gas
        currTotalIdle: uint256 = self.totalIdle
        currTotalDebt: uint256 = self.totalDebt

        # withdraw from strategies if insufficient total idle
        assetsNeeded: uint256 = assets - currTotalIdle
        assetsToWithdraw: uint256 = 0
        for strategy in _strategies:
            assert self.strategies[strategy].activation != 0, "inactive strategy"

            assetsToWithdraw = min(assetsNeeded, IStrategy(strategy).withdrawable())
            # continue if nothing to withdraw
            if assetsToWithdraw == 0:
                continue

            IStrategy(strategy).freeFunds(assetsToWithdraw)
            ASSET.transferFrom(strategy, self, assetsToWithdraw)
            currTotalIdle += assetsToWithdraw
            currTotalDebt -= assetsToWithdraw
            self.strategies[strategy].currentDebt -= assetsToWithdraw

            # break if we have enough total idle
            if assets <= currTotalIdle:
                break

            assetsNeeded -= assetsToWithdraw

        # if we exhaust the queue and still have insufficient total idle, revert
        assert currTotalIdle >= assets, "insufficient total idle"
        # commit memory to storage
        self.totalIdle = currTotalIdle
        self.totalDebt = currTotalDebt

    self._burnShares(_shares, _owner)
    self.totalIdle -= assets
    self.erc20_safe_transfer(ASSET.address, _receiver, assets)

    log Withdraw(_sender, _receiver, _owner, assets, _shares)

    return assets


# SHARE MANAGEMENT FUNCTIONS #
@view
@external
def totalAssets() -> uint256:
    return self._totalAssets()

@external
def convertToShares(assets: uint256) -> uint256:
   return self._convertToShares(assets)

@external
def convertToAssets(shares: uint256) -> uint256:
   return self._convertToAssets(shares)

@external
def maxDeposit(receiver: address) -> uint256:
   # TODO: implement deposit limit
   return MAX_UINT256

@external
def maxMint(receiver: address) -> uint256:
   maxDeposit: uint256 = MAX_UINT256
   return self._convertToShares(maxDeposit)

@external
def maxWithdraw(owner: address) -> uint256:
   # TODO: calculate max between liquidity
   # TODO: take this into account when implementing withdrawing from custom strategies
   return self._convertToAssets(self.balanceOf[owner])

@external
def maxRedeem(owner: address) -> uint256:
   # TODO: add max liquidity calculation
   # TODO: take this into account when implementing withdrawing from custom strategies
   return self.balanceOf[owner]

@external
def previewDeposit(assets: uint256) -> uint256:
   return self._convertToShares(assets)

@external
def previewMint(shares: uint256) -> uint256:
   return self._convertToAssets(shares)

@external
def previewWithdraw(shares: uint256) -> uint256:
    return self._convertToAssets(shares)

@external
def previewRedeem(shares: uint256) -> uint256:
   return self._convertToAssets(shares)

@external
def deposit(assets: uint256, receiver: address) -> uint256:
       return self._deposit(msg.sender, receiver, assets)

@external
def mint(shares: uint256, receiver: address) -> uint256:
   assets: uint256 = self._convertToAssets(shares)
   self._deposit(msg.sender, receiver, assets)
   return assets

@external
def withdraw(_assets: uint256, _receiver: address, _owner: address) -> uint256:
   shares: uint256 = self._convertToShares(_assets)
   # TODO: withdrawal queue is empty here. Do we need to implement a custom withdrawal queue?
   self._redeem(msg.sender, _receiver, _owner, shares, [])
   return shares

@external
def redeem(_shares: uint256, _receiver: address, _owner: address) -> uint256:
   assets: uint256 = self._redeem(msg.sender, _receiver, _owner, _shares, [])
   return assets

# SHARE MANAGEMENT FUNCTIONS #
@view
@external
def pricePerShare() -> uint256:
    return self._convertToAssets(10 ** DECIMALS)

@view
@external
def availableDepositLimit() -> uint256:
    if self.depositLimit > self._totalAssets():
        return self.depositLimit - self._totalAssets()
    return 0


# STRATEGY MANAGEMENT FUNCTIONS #
@external
def addStrategy(new_strategy: address):
    self._enforce_role(msg.sender, Roles.STRATEGY_MANAGER)
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
    self._enforce_role(msg.sender, Roles.STRATEGY_MANAGER)
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
    self._enforce_role(msg.sender, Roles.STRATEGY_MANAGER)
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
    self._enforce_role(msg.sender, Roles.DEBT_MANAGER)
    assert self.strategies[strategy].activation != 0, "inactive strategy"
    # TODO: should we check that totalMaxDebt is not over 100% of assets?
    self.strategies[strategy].maxDebt = new_maxDebt

    log UpdatedMaxDebtForStrategy(msg.sender, strategy, new_maxDebt)


@external
def updateDebt(strategy: address) -> uint256:
    self._enforce_role(msg.sender, Roles.DEBT_MANAGER)
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
        assetsToWithdraw: uint256 = currentDebt - newDebt
        withdrawable: uint256 = IStrategy(strategy).withdrawable()
        assert withdrawable != 0, "nothing to withdraw"

        # if insufficient withdrawable, withdraw what we can
        if (withdrawable < assetsToWithdraw):
            assetsToWithdraw = withdrawable
            newDebt = currentDebt - withdrawable

        IStrategy(strategy).freeFunds(assetsToWithdraw)
	# TODO: is it worth it to transfer the maxAmount between assetsToWithdraw and balance?
        ASSET.transferFrom(strategy, self, assetsToWithdraw)
        self.totalIdle += assetsToWithdraw
        self.totalDebt -= assetsToWithdraw
    else:
        # increase debt
        assetsToTransfer: uint256 = newDebt - currentDebt
        # if insufficient funds to deposit, transfer only what is free
        if assetsToTransfer > self.totalIdle:
            assetsToTransfer = self.totalIdle
            newDebt = currentDebt + assetsToTransfer
        ASSET.transfer(strategy, assetsToTransfer)
        self.totalIdle -= assetsToTransfer
        self.totalDebt += assetsToTransfer

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

# def setFeeManager(newFeeManager: address):
#     # TODO: change feemanager contract
#     return

# Role management
@external
def set_role(account: address, role: Roles):
    assert msg.sender == self.role_manager
    self.roles[account] = role

@internal
def _enforce_role(account: address, role: Roles):
    assert role in self.roles[account] # dev: not allowed

@external
def transfer_role_manager(role_manager: address):
    assert msg.sender == self.role_manager
    self.future_role_manager = role_manager

@external
def accept_role_manager():
    assert msg.sender == self.future_role_manager
    self.role_manager = msg.sender
    self.future_role_manager = ZERO_ADDRESS
