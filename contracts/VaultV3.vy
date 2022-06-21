# @version 0.3.3

from vyper.interfaces import ERC20

# TODO: external contract: factory
# TODO: external contract: access control
# TODO: external contract: fee manager
# TODO: external contract: healtcheck

# INTERFACES #
interface ERC20Metadata:
    def decimals() -> uint8: view

interface IYVaultDepositCallback:
   def yVaultDepositCallback(amount: uint256, depositor: address): nonpayable

interface IStrategy:
   def asset() -> address: view
   def vault() -> address: view
   
# EVENTS #
event StrategyAdded: 
   strategy: indexed(address)

event StrategyRevoked: 
   strategy: indexed(address)

event Deposit:
    fnCaller: indexed(address)
    owner: indexed(address)
    assets: uint256 
    shares: uint256

event Withdraw:
    fnCaller: indexed(address)
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


# STRUCTS #
# TODO: strategy params
struct StrategyParams:
   activation: uint256
   currentDebt: uint256
   maxDebt: uint256

# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000

# STORAGE #
ASSET: immutable(ERC20)
strategies: public(HashMap[address, StrategyParams])
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])

totalSupply: public(uint256)
totalDebt: public(uint256)
totalIdle: public(uint256)

name: public(String[64])
symbol: public(String[32])
decimals: public(uint256)

# `nonces` track `permit` approvals with signature.
nonces: public(HashMap[address, uint256])
DOMAIN_SEPARATOR: public(bytes32)
DOMAIN_TYPE_HASH: constant(bytes32) = keccak256('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
PERMIT_TYPE_HASH: constant(bytes32) = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)")

@external
def __init__(asset: ERC20):
    ASSET = asset
    self.decimals = convert(ERC20Metadata(asset.address).decimals(), uint256)
    # TODO: implement
    return

## ERC20 ##
@internal
def _spendAllowance(owner: address, fnCaller: address, amount: uint256):
   self.allowance[owner][fnCaller] -= amount

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
@internal
def _totalAssets() -> uint256:
    return self.totalIdle + self.totalDebt

@view
@internal
def _amountForShares(shares: uint256) -> uint256:
    _totalSupply: uint256 = self.totalSupply
    amount: uint256 = shares
    if _totalSupply > 0:
        amount = shares * self._totalAssets() / self.totalSupply
    return amount

@view
@internal
def _sharesForAmount(amount: uint256) -> uint256:
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
def _burnShares(shares: uint256, owner: address):
    # TODO: do we need to check?
    self.balanceOf[owner] -= shares
    self.totalSupply -= shares


@internal
def _issueSharesForAmount(amount: uint256, recipient: address) -> uint256:
    newShares: uint256 = self._sharesForAmount(amount)
    assert newShares > 0

    self.balanceOf[recipient] += newShares
    self.totalSupply += newShares

    return newShares

@internal
def _deposit(_fnCaller: address, _recipient: address, amount: uint256) -> uint256:
    assert _recipient not in [self, ZERO_ADDRESS], "invalid recipient"
    
    shares: uint256 = self._issueSharesForAmount(amount, _recipient)

    self.erc20_safe_transferFrom(ASSET.address, msg.sender, self, amount)
    self.totalIdle += amount

    log Deposit(_fnCaller, _recipient, amount, shares)

    return shares

@internal
def _redeem(fnCaller: address, _receiver: address, _owner: address, _shares: uint256, _strategies: DynArray[address, 10] = []) -> uint256:
    if fnCaller != _owner: 
      self._spendAllowance(_owner, msg.sender, _shares)

    assets: uint256 = self._amountForShares(_shares)

    # TODO: withdraw from strategies
    
    # TODO: gas savings: totalIdle should be cached if used above
    assert self.totalIdle >= assets, "insufficient total idle"

    self._burnShares(_shares, _owner)

    self.totalIdle -= assets
    self.erc20_safe_transfer(ASSET.address, _receiver, assets)

    log Withdraw(msg.sender, _receiver, _owner, _shares, assets)

    return assets


## ERC4626 ## 
@external
def asset() -> address:
   return ASSET.address

@view
@external
def totalAssets() -> uint256:
    return self._totalAssets()

@external
def convertToShares(assets: uint256) -> uint256:
   return self._sharesForAmount(assets)

@external
def convertToAssets(shares: uint256) -> uint256:
   return self._amountForShares(shares)

@external
def maxDeposit(owner: address) -> uint256:
   return MAX_UINT256

@external
def maxMint(owner: address) -> uint256: 
   maxDeposit: uint256 = MAX_UINT256
   return self._sharesForAmount(maxDeposit)

@external
def maxWithdraw(owner: address) -> uint256:
   # TODO: calculate max between liquidity and shares
   return 0

@external
def maxRedeem(owner: address) -> uint256:
   # TODO: add max liquidity calculation
   return self.balanceOf[owner]

@external
def previewDeposit(assets: uint256) -> uint256:
   return self._sharesForAmount(assets)

@external
def previewWithdraw(shares: uint256) -> uint256:
    return self._amountForShares(shares)

@external
def deposit(assets: uint256, receiver: address) -> uint256:
       return self._deposit(msg.sender, receiver, assets)

@external
def mint(shares: uint256, receiver: address) -> uint256:
   assets: uint256 = self._amountForShares(shares)
   self._deposit(msg.sender, receiver, assets)
   return assets

@external
def withdraw(_assets: uint256, _receiver: address, _owner: address) -> uint256:
   shares: uint256 = self._sharesForAmount(_assets)
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
    return self._amountForShares(10 ** self.decimals)

# STRATEGY MANAGEMENT FUNCTIONS #
@external
def addStrategy(new_strategy: address):
   # TODO: permissioned: STRATEGY_MANAGER
   assert new_strategy != ZERO_ADDRESS
   assert self == IStrategy(new_strategy).vault()
   assert self.strategies[new_strategy].activation == 0
   assert IStrategy(new_strategy).asset() != ASSET.address
   
   self.strategies[new_strategy] = StrategyParams({
      activation: block.timestamp,
      currentDebt: 0,
      maxDebt: 0
   })

   log StrategyAdded(new_strategy)

   return

@internal
def _revokeStrategy(old_strategy: address):
   # TODO: permissioned: STRATEGY_MANAGER
   assert self.strategies[old_strategy].activation != 0
   # NOTE: strategy needs to have 0 debt to be revoked
   assert self.strategies[old_strategy].currentDebt == 0

   # NOTE: strategy params are set to 0 (warning: it can be readded)
   self.strategies[old_strategy] = StrategyParams({
       activation: 0,
       currentDebt: 0,
       maxDebt: 0
   })

   log StrategyRevoked(old_strategy)

   return

@external
def revokeStrategy(old_strategy: address):
    self._revokeStrategy(old_strategy)

@external
def migrateStrategy(new_strategy: address, old_strategy: address):
   # TODO: permissioned: STRATEGY_MANAGER

    # TODO: add strategy migrated event? 
    assert self.strategies[old_strategy].activation != 0
    assert self.strategies[old_strategy].currentDebt == 0

    migrated_strategy: StrategyParams = self.strategies[old_strategy]

    # NOTE: we add strategy with same params than the strategy being migrated
    self.strategies[new_strategy] = StrategyParams({
       activation: block.timestamp,
       currentDebt: migrated_strategy.currentDebt,
       maxDebt: migrated_strategy.maxDebt
    })

    self._revokeStrategy(old_strategy)

    return
 
@external
def updateMaxDebtForStrategy(strategy: address, new_maxDebt: uint256): 
   # TODO: permissioned: DEBT_MANAGER 
   assert self.strategies[strategy].activation != 0
   # TODO: should we check that totalMaxDebt is not over 100% of assets? 
   self.strategies[strategy].maxDebt = new_maxDebt
   return

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



