# @version 0.3.4

from vyper.interfaces import ERC20

# TODO: external contract: factory
# TODO: external contract: access control
# TODO: external contract: fee manager
# TODO: external contract: healtcheck

# INTERFACES #
interface ERC20Metadata:
    def decimals() -> uint8: view

interface IStrategy:
   def asset() -> address: view
   def vault() -> address: view

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

# STRUCTS #
# TODO: strategy params
struct StrategyParams:
    activation: uint256
    currentDebt: uint256
    maxDebt: uint256

# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000


# IMUTABLE #
asset: immutable public(ERC20)
decimals: immutable public(uint256)

# STORAGE #
strategies: public(HashMap[address, StrategyParams])
balanceOf: public(HashMap[address, uint256])
totalSupply: public(uint256)
totalDebt: public(uint256)
totalIdle: public(uint256)


@external
def __init__(asset: ERC20):
    self.asset = asset
    self.decimals = convert(ERC20Metadata(asset.address).decimals(), uint256)
    # TODO: implement
    return


# SUPPORT FUNCTIONS #
@view
@internal
def _totalAssets() -> uint256:
    return self.totalIdle + self.totalDebt


@internal
def _burnShares(shares: uint256, owner: address):
    # TODO: do we need to check?
    self.balanceOf[owner] -= shares
    self.totalSupply -= shares


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
        amount = self.asset.balanceOf(msg.sender)

    assert amount > 0, "cannot deposit zero"
    # TODO: should it check deposit limit?

    shares: uint256 = self._issueSharesForAmount(amount, _recipient)

    self.erc20_safe_transferFrom(self.asset.address, msg.sender, self, amount)
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

    self.erc20_safe_transfer(self.asset.address, _recipient, amount)

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
    return self._amountForShares(10 ** self.decimals)


@external
def sharesForAmount(amount: uint256) -> uint256:
    return self._sharesForAmount(amount)


@external
def amountForShares(shares: uint256) -> uint256:
    return self._amountForShares(shares)


# STRATEGY MANAGEMENT FUNCTIONS #
@external
def addStrategy(new_strategy: address):
    # TODO: permissioned: STRATEGY_MANAGER
    assert new_strategy != ZERO_ADDRESS, "strategy cannot be zero address"
    assert IStrategy(new_strategy).asset() == self.asset.address, "invalid asset"
    assert IStrategy(new_strategy).vault() == self, "invalid vault"
    assert self.strategies[new_strategy].activation == 0, "strategy already active"

    self.strategies[new_strategy] = StrategyParams({
        activation: block.timestamp,
        currentDebt: 0,
        maxDebt: 0
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
        currentDebt: 0,
        maxDebt: 0
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
    assert IStrategy(new_strategy).asset() == self.asset.address, "invalid asset"
    assert IStrategy(new_strategy).vault() == self, "invalid vault"
    assert self.strategies[new_strategy].activation == 0, "strategy already active"

    migrated_strategy: StrategyParams = self.strategies[old_strategy]

    # NOTE: we add strategy with same params than the strategy being migrated
    self.strategies[new_strategy] = StrategyParams({
       activation: block.timestamp,
       currentDebt: migrated_strategy.currentDebt,
       maxDebt: migrated_strategy.maxDebt
    })

    self._revokeStrategy(old_strategy)

    log StrategyMigrated(old_strategy, new_strategy)


@external
def updateMaxDebtForStrategy(strategy: address, new_maxDebt: uint256):
    # TODO: permissioned: DEBT_MANAGER
    assert self.strategies[strategy].activation != 0
    # TODO: should we check that totalMaxDebt is not over 100% of assets?
    self.strategies[strategy].maxDebt = new_maxDebt
    # TODO: should this emit an event?

# # P&L MANAGEMENT FUNCTIONS #
# def processReport(strategy: address):
#     # permissioned: ACCOUNTING_MANAGER (open?)
#     # TODO: calculate the P&L of the strategy and save the new status
#     # the way is to compare the strategy's assets with the debt with the vault
#     # strategy_assets > strategy_debt? profit. else loss
#     #    - lock the profit !
#     #    - implement the healthcheck
#     return

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

# def updateDebt():
#     # permissioned: DEBT_MANAGER (or maybe open?)
#     # TODO: rebalance debt. if the strategy is allowed to take more debt and the strategy wants that debt, the vault will send more. if the strategy has too much debt, the vault will have less
#     #    - retrieve current position
#     #    - retrieve max debt allocated
#     #    - check the strategy wants that debt
#     #    -
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



