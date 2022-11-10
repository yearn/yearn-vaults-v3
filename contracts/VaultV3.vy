# @version 0.3.7

from vyper.interfaces import ERC20
from vyper.interfaces import ERC4626
from vyper.interfaces import ERC20Detailed

# INTERFACES #
interface IStrategy:
    def asset() -> address: view
    def vault() -> address: view
    def balanceOf(owner: address) -> uint256: view
    def maxDeposit(receiver: address) -> uint256: view
    def maxWithdraw(owner: address) -> uint256: view
    def withdraw(amount: uint256, receiver: address, owner: address) -> uint256: nonpayable
    def deposit(assets: uint256, receiver: address) -> uint256: nonpayable
    def totalAssets() -> (uint256): view
    def convertToAssets(shares: uint256) -> (uint256): view
    def convertToShares(assets: uint256) -> (uint256): view

interface IAccountant:
    def report(strategy: address, gain: uint256, loss: uint256) -> (uint256, uint256): nonpayable

# EVENTS #
# ERC4626 EVENTS
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

# ERC20 EVENTS
event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

# STRATEGY MANAGEMENT EVENTS
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
    current_debt: uint256
    total_fees: uint256
    total_refunds: uint256

# DEBT MANAGEMENT EVENTS
event DebtUpdated:
    strategy: address
    current_debt: uint256
    new_debt: uint256

# STORAGE MANAGEMENT EVENTS
event UpdateAccountant:
    accountant: address

event UpdatedMaxDebtForStrategy:
    sender: address
    strategy: address
    new_debt: uint256

event UpdateDepositLimit:
    deposit_limit: uint256

event UpdateMinimumTotalIdle:
    minimum_total_idle: uint256

event Shutdown:
    pass

event Sweep:
    token: indexed(address)
    amount: uint256

# STRUCTS #
struct StrategyParams:
    activation: uint256
    last_report: uint256
    current_debt: uint256
    max_debt: uint256

# CONSTANTS #
MAX_BPS: constant(uint256) = 1_000_000_000_000

# ENUMS #
enum Roles:
    STRATEGY_MANAGER
    DEBT_MANAGER
    EMERGENCY_MANAGER
    ACCOUNTING_MANAGER

# IMMUTABLE #
ASSET: immutable(ERC20)
DECIMALS: immutable(uint256)
PROFIT_MAX_UNLOCK_TIME: immutable(uint256)

# CONSTANTS #
API_VERSION: constant(String[28]) = "0.1.0"
# TODO: make this variable immutable
PROFIT_MAX_UNLOCK_TIME: constant(uint256) = 2 * 7 * 24 * 3600

# STORAGE #
# HashMap that records all the strategies that are allowed to receive assets from the vault
strategies: public(HashMap[address, StrategyParams])
# ERC20 - amount of shares per account
balance_of: HashMap[address, uint256]
# ERC20 - owner -> (spender -> amount)
allowance: public(HashMap[address, HashMap[address, uint256]])

# Total amount of shares that are currently minted
total_supply: public(uint256)
# Total amount of assets that has been deposited in strategies
<<<<<<< HEAD
total_debt: public(uint256)
=======
total_debt: uint256
>>>>>>> bd63e74 (feat: implement no sandwiching using share burning and minting)
# Current assets held in the vault contract. Replacing balanceOf(this) to avoid price_per_share manipulation
total_idle: public(uint256)
# Minimum amount of assets that should be kept in the vault contract to allow for fast, cheap redeems
minimum_total_idle: public(uint256)
# Maximum amount of tokens that the vault can accept. If totalAssets > deposit_limit, deposits will revert
deposit_limit: public(uint256)
accountant: public(address)
# HashMap mapping addresses to their roles
roles: public(HashMap[address, Roles])
# HashMap mapping roles to their permissioned state. If false, the role is not open to the public
open_roles: public(HashMap[Roles, bool])
# Address that can add and remove addresses to roles 
role_manager: public(address)
# Temporary variable to store the address of the next role_manager until the role is accepted
future_role_manager: public(address)
# State of the vault - if set to true, only withdrawals will be available. It can't be reverted
shutdown: public(bool)

# ERC20 - name of the token
name: public(String[64])
# ERC20 - symbol of the token
symbol: public(String[32])

<<<<<<< HEAD
full_profit_unlock_date: public(uint256)
profit_unlocking_rate: public(uint256)
=======
full_profit_unlock_date: uint256
profit_unlocking_rate: uint256
>>>>>>> bd63e74 (feat: implement no sandwiching using share burning and minting)
last_profit_update: uint256

# `nonces` track `permit` approvals with signature.
nonces: public(HashMap[address, uint256])
DOMAIN_TYPE_HASH: constant(bytes32) = keccak256('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
PERMIT_TYPE_HASH: constant(bytes32) = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)")

# Constructor
@external
def __init__(asset: ERC20, name: String[64], symbol: String[32], role_manager: address, profit_max_unlock_time: uint256):
    ASSET = asset
    DECIMALS = convert(ERC20Detailed(asset.address).decimals(), uint256)
    assert 10 ** (2 * DECIMALS) <= max_value(uint256) # dev: token decimals too high
    
    PROFIT_MAX_UNLOCK_TIME = profit_max_unlock_time

    self.name = name
    self.symbol = symbol

    self.role_manager = role_manager
    self.shutdown = False

## SHARE MANAGEMENT ##
## ERC20 ##
@internal
def _spend_allowance(owner: address, spender: address, amount: uint256):
    # Unlimited approval does nothing (saves an SSTORE)
    if (self.allowance[owner][spender] < max_value(uint256)):
        current_allowance: uint256 = self.allowance[owner][spender]
        assert current_allowance >= amount, "insufficient allowance"
        self._approve(owner, spender, current_allowance - amount)

@internal
def _transfer(sender: address, receiver: address, amount: uint256):
    # Protect people from accidentally sending their shares to bad places
    assert self.balance_of[sender] >= amount, "insufficient funds"
    self.balance_of[sender] -= amount
    self.balance_of[receiver] += amount
    log Transfer(sender, receiver, amount)

@internal
def _transfer_from(sender: address, receiver: address, amount: uint256) -> bool:
    self._spend_allowance(sender, msg.sender, amount)
    self._transfer(sender, receiver, amount)
    return True

@internal
def _approve(owner: address, spender: address, amount: uint256) -> bool:
    self.allowance[owner][spender] = amount
    log Approval(owner, spender, amount)
    return True

@internal
def _increase_allowance(owner: address, spender: address, amount: uint256) -> bool:
    self.allowance[owner][spender] += amount
    log Approval(owner, spender, self.allowance[owner][spender])
    return True

@internal
def _decrease_allowance(owner: address, spender: address, amount: uint256) -> bool:
    self.allowance[owner][spender] -= amount
    log Approval(owner, spender, self.allowance[owner][spender])
    return True

# TODO: review correct implementation
@internal
def _permit(owner: address, spender: address, amount: uint256, deadline: uint256, v: uint8, r: bytes32, s: bytes32) -> bool:
    assert owner != empty(address), "invalid owner"
    assert deadline >= block.timestamp, "permit expired"
    nonce: uint256 = self.nonces[owner]
    digest: bytes32 = keccak256(
        concat(
            b'\x19\x01',
            self.domain_separator(),
            keccak256(
                concat(
                    PERMIT_TYPE_HASH,
                    convert(owner, bytes32),
                    convert(spender, bytes32),
                    convert(amount, bytes32),
                    convert(nonce, bytes32),
                    convert(deadline, bytes32),
                )
            )
        )
    )
    assert ecrecover(digest, convert(v, uint256), convert(r, uint256), convert(s, uint256)) == owner, "invalid signature"
    self.allowance[owner][spender] = amount
    self.nonces[owner] = nonce + 1
    log Approval(owner, spender, amount)
    return True

@view
@external
def unlocked_shares() -> uint256:
  return self._unlocked_shares()

@view
@internal
def _unlocked_shares() -> uint256:
  _full_profit_unlock_date: uint256 = self.full_profit_unlock_date
  unlocked_shares: uint256 = 0
  if _full_profit_unlock_date > block.timestamp:
    unlocked_shares = self.profit_unlocking_rate * (block.timestamp - self.last_profit_update) / MAX_BPS
  elif _full_profit_unlock_date != 0:
    # All shares have been unlocked
    unlocked_shares = self.balance_of[self]

  return unlocked_shares

@view
@internal
def _total_supply() -> uint256:
  return self.total_supply - self._unlocked_shares()

@internal
def _burn_unlocked_shares() -> uint256:
  unlocked_shares: uint256 = self._unlocked_shares()
  if unlocked_shares == 0:
    return 0
  
  # update variables (done here to keep _unlocked_shares as a view function)
  if self.full_profit_unlock_date > block.timestamp:
    self.last_profit_update = block.timestamp
  else:
    self.profit_unlocking_rate = 0

  self._burn_shares(unlocked_shares, self)
  return unlocked_shares

@view
@internal
def _unlocked_shares() -> uint256:
  _full_profit_unlock_date: uint256 = self.full_profit_unlock_date
  unlocked_shares: uint256 = 0
  if _full_profit_unlock_date > block.timestamp:
    unlocked_shares = self.profit_unlocking_rate * (block.timestamp - self.last_profit_update)
  else:
    # All shares have been unlocked
    unlocked_shares = self.profit_unlocking_rate * (_full_profit_unlock_date - self.last_profit_update)
  return unlocked_shares

@view
@internal
def _total_supply() -> uint256:
  return self.total_supply - self._unlocked_shares()

@internal
def _burn_unlocked_shares() -> uint256:
  unlocked_shares: uint256 = self._unlocked_shares()

  if self.full_profit_unlock_date > block.timestamp:
    self.last_profit_update = block.timestamp
  else:
    self.profit_unlocking_rate = 0

  self._burn_shares(unlocked_shares, self)
  return unlocked_shares

@view
@internal
def _total_assets() -> uint256:
    """
    Total amount of assets that are in the vault and in the strategies. 
    """
    return self.total_idle + self.total_debt

@internal
def _burn_shares(shares: uint256, owner: address):
    self.balance_of[owner] -= shares
    self.total_supply -= shares
    log Transfer(owner, empty(address), shares)

@view
@internal
def _convert_to_assets(shares: uint256) -> uint256:
    """ 
    assets = shares * (total_assets / total_supply) --- (== price_per_share * shares)
    """
    _total_supply: uint256 = self._total_supply()
    # if total_supply is 0, price_per_share is 1
    if _total_supply == 0: 
        return shares

    amount: uint256 = shares * self._total_assets() / _total_supply
    return amount

@view
@internal
def _convert_to_shares(assets: uint256) -> uint256:
    """
    shares = amount * (total_supply / total_assets) --- (== amount / price_per_share)
    """
    _total_supply: uint256 = self._total_supply()

    # if total_supply is 0, price_per_share is 1
    if _total_supply == 0:
       return assets

    shares: uint256 = assets * _total_supply / self._total_assets()
    return shares


# TODO: review in detail
@internal
def erc20_safe_approve(token: address, spender: address, amount: uint256):
    # Used only to send tokens that are not the type managed by this Vault.
    # HACK: Used to handle non-compliant tokens like USDT
    response: Bytes[32] = raw_call(
        token,
        concat(
            method_id("approve(address,uint256)"),
            convert(spender, bytes32),
            convert(amount, bytes32),
        ),
        max_outsize=32,
    )
    if len(response) > 0:
        assert convert(response, bool), "Transfer failed!"


@internal
def erc20_safe_transfer_from(token: address, sender: address, receiver: address, amount: uint256):
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

# TODO: review in detail
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
def _issue_shares_for_amount(amount: uint256, recipient: address) -> uint256:
    # NOTE: we update total supply
    self._burn_unlocked_shares()
    new_shares: uint256 = self._convert_to_shares(amount)

    # We don't make the function revert
    if new_shares == 0:
       return 0

    self.balance_of[recipient] += new_shares
    self.total_supply += new_shares

    log Transfer(empty(address), recipient, new_shares)
    return new_shares

## ERC4626 ##
@view
@internal
def _max_deposit(receiver: address) -> uint256:
    _total_assets: uint256 = self._total_assets()
    _deposit_limit: uint256 = self.deposit_limit
    if (_total_assets >= _deposit_limit):
        return 0

    return _deposit_limit - _total_assets

@view
@internal
def _max_redeem(owner: address) -> uint256:
    # NOTE: this will return the max amount that is available to redeem using ERC4626 (which can only withdraw from the vault contract)
    return min(self.balance_of[owner], self._convert_to_shares(self.total_idle))


@internal
def _deposit(_sender: address, _recipient: address, _assets: uint256) -> uint256:
    assert self.shutdown == False # dev: shutdown
    assert _recipient not in [self, empty(address)], "invalid recipient"
    assets: uint256 = _assets
    # If the amount is max_value(uint256) we assume the user wants to deposit their whole balance
    if assets == max_value(uint256):
        assets = ASSET.balanceOf(_sender)

    assert self._total_assets() + assets <= self.deposit_limit, "exceed deposit limit"
    
    shares: uint256 = self._issue_shares_for_amount(assets, _recipient)
    assert shares > 0, "cannot mint zero"

    self.erc20_safe_transfer_from(ASSET.address, msg.sender, self, assets)
    self.total_idle += assets

    log Deposit(_sender, _recipient, assets, shares)

    return shares

@internal
def _assess_share_of_unrealised_losses(strategy: address, assets_needed: uint256) -> uint256:
    # NOTE: the function returns the share of losses that a user should take if withdrawing from this strategy
    strategy_current_debt: uint256 = self.strategies[strategy].current_debt
    assets_to_withdraw: uint256 = min(assets_needed, strategy_current_debt)
    vault_shares: uint256 = IStrategy(strategy).balanceOf(self)
    strategy_assets: uint256 = IStrategy(strategy).convertToAssets(vault_shares)
    
    # If no losses, return 0
    if strategy_assets >= strategy_current_debt or strategy_current_debt == 0:
        return 0

    # user will withdraw assets_to_withdraw divided by loss ratio (strategy_assets / strategy_current_debt - 1)
    # but will only receive assets_to_withdrar
    # NOTE: if there are unrealised losses, the user will take his share
    losses_user_share: uint256 = assets_to_withdraw - assets_to_withdraw * strategy_assets / strategy_current_debt
    return losses_user_share


@internal
def _redeem(sender: address, receiver: address, owner: address, shares_to_burn: uint256, strategies: DynArray[address, 10] = []) -> uint256:
    if sender != owner:
        self._spend_allowance(owner, sender, shares_to_burn)

    shares: uint256 = shares_to_burn
    shares_balance: uint256 = self.balance_of[owner]

    if shares == max_value(uint256):
        shares = shares_balance

    assert shares_balance >= shares, "insufficient shares to redeem"
    assert shares > 0, "no shares to redeem"

    requested_assets: uint256 = self._convert_to_assets(shares)

    # load to memory to save gas
    curr_total_idle: uint256 = self.total_idle
    
    # If there are not enough assets in the Vault contract, we try to free funds from strategies specified in the input
    if requested_assets > curr_total_idle:
        # load to memory to save gas
        curr_total_debt: uint256 = self.total_debt

        # Withdraw from strategies if insufficient total idle
        assets_needed: uint256 = requested_assets - curr_total_idle
        assets_to_withdraw: uint256 = 0

        # NOTE: to compare against real withdrawals from strategies
        previous_balance: uint256 = ASSET.balanceOf(self)
        for strategy in strategies:
            assert self.strategies[strategy].activation != 0, "inactive strategy"
          
            # Starts with all the assets needed
            assets_to_withdraw = assets_needed

            # CHECK FOR UNREALISED LOSSES
            # If unrealised losses > 0, then the user will take the proportional share and realise it (required to avoid users withdrawing from lossy strategies) 
            # NOTE: assets_to_withdraw will be capped to strategy's current_debt within the function
            unrealised_losses_share: uint256 = self._assess_share_of_unrealised_losses(strategy, assets_to_withdraw)
            if unrealised_losses_share > 0:
                # User now "needs" less assets to be unlocked (as he took some as losses)
                assets_to_withdraw -= unrealised_losses_share
                requested_assets -= unrealised_losses_share
                # NOTE: done here instead of waiting for regular update of these values because it's a rare case (so we can save minor amounts of gas)
                assets_needed -= unrealised_losses_share
                curr_total_debt -= unrealised_losses_share
            
            # After losses are taken, vault asks what is the max amount to withdraw
            assets_to_withdraw = min(assets_to_withdraw, IStrategy(strategy).maxWithdraw(self))

            # continue to next strategy if nothing to withdraw
            if assets_to_withdraw == 0:
                continue

            # WITHDRAW FROM STRATEGY
            IStrategy(strategy).withdraw(assets_to_withdraw, self, self)
            post_balance: uint256 = ASSET.balanceOf(self)
            
            # If we have not received what we expected, we consider the difference a loss
            loss: uint256 = 0
            if(previous_balance + assets_to_withdraw > post_balance):
              loss = previous_balance + assets_to_withdraw - post_balance

            # NOTE: we update the previous_balance variable here to save gas in next iteration
            previous_balance = post_balance
 
            # NOTE: strategy's debt decreases by the full amount but the total idle increases 
            # by the actual amount only (as the difference is considered lost)
            curr_total_idle += (assets_to_withdraw - loss)
            requested_assets -= loss
            curr_total_debt -= assets_to_withdraw
            # Vault will reduce debt because the unrealised loss has been taken by user
            self.strategies[strategy].current_debt -= (assets_to_withdraw + unrealised_losses_share)
            # NOTE: the user will receive less tokens (the rest were lost)
            # break if we have enough total idle to serve initial request 
            if requested_assets <= curr_total_idle:
                break

            assets_needed -= assets_to_withdraw

        # if we exhaust the queue and still have insufficient total idle, revert
        assert curr_total_idle >= requested_assets, "insufficient assets in vault"
        # commit memory to storage
        self.total_debt = curr_total_debt

    self._burn_shares(shares, owner)
    # commit memory to storage
    self.total_idle = curr_total_idle - requested_assets
    self.erc20_safe_transfer(ASSET.address, receiver, requested_assets)

    log Withdraw(sender, receiver, owner, requested_assets, shares)
    return requested_assets

## STRATEGY MANAGEMENT ##
@internal
def _add_strategy(new_strategy: address):
   assert new_strategy != empty(address), "strategy cannot be zero address"
   assert IStrategy(new_strategy).asset() == ASSET.address, "invalid asset"
   assert IStrategy(new_strategy).vault() == self, "invalid vault"
   assert self.strategies[new_strategy].activation == 0, "strategy already active"

   self.strategies[new_strategy] = StrategyParams({
      activation: block.timestamp,
      last_report: block.timestamp,
      current_debt: 0,
      max_debt: 0
      })

   log StrategyAdded(new_strategy)

# TODO: add a forcing parameter that ignores that the strategy has debt?
@internal
def _revoke_strategy(old_strategy: address):
   assert self.strategies[old_strategy].activation != 0, "strategy not active"
   assert self.strategies[old_strategy].current_debt == 0, "strategy has debt"

   # NOTE: strategy params are set to 0 (WARNING: it can be readded)
   self.strategies[old_strategy] = StrategyParams({
      activation: 0,
      last_report: 0,
      current_debt: 0,
      max_debt: 0
      })

   log StrategyRevoked(old_strategy)

@internal
def _migrate_strategy(new_strategy: address, old_strategy: address):
    assert self.strategies[old_strategy].activation != 0, "old strategy not active"
    assert self.strategies[old_strategy].current_debt == 0, "old strategy has debt"
    assert new_strategy != empty(address), "strategy cannot be zero address"
    assert IStrategy(new_strategy).asset() == ASSET.address, "invalid asset"
    assert IStrategy(new_strategy).vault() == self, "invalid vault"
    assert self.strategies[new_strategy].activation == 0, "strategy already active"

    migrated_strategy: StrategyParams = self.strategies[old_strategy]

    # NOTE: we add strategy with same params than the strategy being migrated
    self.strategies[new_strategy] = StrategyParams({
       activation: block.timestamp,
       last_report: block.timestamp,
       current_debt: migrated_strategy.current_debt,
       max_debt: migrated_strategy.max_debt
       })

    self._revoke_strategy(old_strategy)

    log StrategyMigrated(old_strategy, new_strategy)

# DEBT MANAGEMENT #
@internal
def _update_debt(strategy: address, target_debt: uint256) -> uint256:
    """
    The vault will rebalance the debt vs target debt. Target debt must be smaller or equal strategy max_debt.
    This function will compare the current debt with the target debt and will take funds or deposit new 
    funds to the strategy. 

    The strategy can require a minimum (or a maximum) amount of funds that it wants to receive to invest. 
    The strategy can also reject freeing funds if they are locked.

    The vault will not invest the funds into the underlying protocol, which is responsibility of the strategy. 
    """
    new_debt: uint256 = target_debt

    current_debt: uint256 = self.strategies[strategy].current_debt

    if self.shutdown:
        new_debt = 0

    assert new_debt != current_debt, "new debt equals current debt"

    if current_debt > new_debt:
        # reduce debt
        assets_to_withdraw: uint256 = current_debt - new_debt

        # ensure we always have minimum_total_idle when updating debt
        minimum_total_idle: uint256 = self.minimum_total_idle
        total_idle: uint256 = self.total_idle
        
        # Respect minimum total idle in vault
        if total_idle + assets_to_withdraw < minimum_total_idle:
            assets_to_withdraw = minimum_total_idle - total_idle
            if assets_to_withdraw > current_debt:
                assets_to_withdraw = current_debt
            new_debt = current_debt - assets_to_withdraw

        withdrawable: uint256 = IStrategy(strategy).maxWithdraw(self)
        assert withdrawable != 0, "nothing to withdraw"

        # if insufficient withdrawable, withdraw what we can
        if withdrawable < assets_to_withdraw:
            assets_to_withdraw = withdrawable
            new_debt = current_debt - withdrawable

        # If there are unrealised losses we don't let the vault reduce its debt
        unrealised_losses_share: uint256 = self._assess_share_of_unrealised_losses(strategy, assets_to_withdraw)
        assert unrealised_losses_share == 0, "strategy has unrealised losses"

        IStrategy(strategy).withdraw(assets_to_withdraw, self, self)
        self.total_idle += assets_to_withdraw
        self.total_debt -= assets_to_withdraw
        
        new_debt = current_debt - assets_to_withdraw
    else:
        # Revert if target_debt cannot be achieved due to configured max_debt for given strategy
        assert new_debt <= self.strategies[strategy].max_debt, "target debt higher than max debt"
        # Vault is increasing debt with the strategy by sending more funds
        max_deposit: uint256 = IStrategy(strategy).maxDeposit(self)

        assets_to_transfer: uint256 = new_debt - current_debt
        if assets_to_transfer > max_deposit:
            assets_to_transfer = max_deposit
        # take into consideration minimum_total_idle
        # HACK: to save gas
        minimum_total_idle: uint256 = self.minimum_total_idle
        total_idle: uint256 = self.total_idle

        assert total_idle > minimum_total_idle, "no funds to deposit"
        available_idle: uint256 = total_idle - minimum_total_idle

        # if insufficient funds to deposit, transfer only what is free
        if assets_to_transfer > available_idle:
            assets_to_transfer = available_idle
            new_debt = current_debt + assets_to_transfer

        if assets_to_transfer > 0:
            self.erc20_safe_approve(ASSET.address, strategy, assets_to_transfer)
            IStrategy(strategy).deposit(assets_to_transfer, self)
            self.erc20_safe_approve(ASSET.address, strategy, 0)
            self.total_idle -= assets_to_transfer
            self.total_debt += assets_to_transfer

        new_debt = current_debt + assets_to_transfer
    
    self.strategies[strategy].current_debt = new_debt

    log DebtUpdated(strategy, current_debt, new_debt)
    return new_debt

## ACCOUNTING MANAGEMENT ##
@internal
def _process_report(strategy: address) -> (uint256, uint256):
    """
    Processing a report means comparing the debt that the strategy has taken with the current amount of funds it is reporting
    If the strategy ows less than it currently have, it means it has had a profit
    Else (assets < debt) it has had a loss

    Different strategies might choose different reporting strategies: pessimistic, only realised P&L, ...
    The best way to report depends on the strategy

    The profit will be distributed following a smooth curve over the next PROFIT_MAX_UNLOCK_TIME seconds. 
    Losses will be taken immediately
    """
    assert self.strategies[strategy].activation != 0, "inactive strategy"
    # Vault needs to assess 
    strategy_shares: uint256 = IStrategy(strategy).balanceOf(self)
    total_assets: uint256 = IStrategy(strategy).convertToAssets(strategy_shares)
    current_debt: uint256 = self.strategies[strategy].current_debt
    
    # Burn shares that have been unlocked since the last update
    self._burn_unlocked_shares()

    gain: uint256 = 0
    loss: uint256 = 0

    if total_assets > current_debt:
        gain = total_assets - current_debt
    else:
        loss = current_debt - total_assets

    # TODO: should we add a very low protocol management fee? (set to factory contract)
    total_fees: uint256 = 0
    total_refunds: uint256 = 0
    accountant: address = self.accountant
    # if accountant is not set, fees and refunds are zero
    if accountant != empty(address):
        total_fees, total_refunds = IAccountant(accountant).report(strategy, gain, loss)
    
    # We calculate the amount of shares that could be insta unlocked to avoid pps changes
    # NOTE: this needs to be done before any pps changes
    shares_to_burn: uint256 = 0 
    if loss + total_fees > 0:
      shares_to_burn = self._convert_to_shares(loss + total_fees)

    newly_locked_shares: uint256 = 0
    if gain > 0:
        # NOTE: vault will issue shares worth the profit to avoid instant pps change
        newly_locked_shares += self._issue_shares_for_amount(gain, self)
        # update current debt after processing management fee
        # NOTE: this will increase total_assets
        self.strategies[strategy].current_debt += gain
        self.total_debt += gain
<<<<<<< HEAD

    if total_fees > 0:
        # if fees are non-zero, issue shares
        self._issue_shares_for_amount(total_fees, accountant)
    
=======
        if gain > total_fees:
          # NOTE: vault will issue shares worth the profit to avoid instant pps change
          newly_locked_shares += self._issue_shares_for_amount(gain - total_fees, self)
    
    # Minting fees after gain computation to ensure fees don't benefit from cheaper pps 
    if total_fees > 0:
        # if fees are non-zero, issue shares
        self._issue_shares_for_amount(total_fees, accountant)

    # if refunds are non-zero, transfer assets
>>>>>>> 2b448a7 (feat: insta unlock losses and fees)
    if total_refunds > 0:
        # if refunds are non-zero, transfer assets
        total_refunds = min(total_refunds, self.balance_of[accountant])
        # Shares received as a refund are locked to avoid sudden pps change (like profits)
        self._transfer(accountant, self, total_refunds)
        newly_locked_shares += total_refunds
 
    # Strategy is reporting a loss
    if loss > 0:
        self.strategies[strategy].current_debt -= loss
        self.total_debt -= loss
 
    # Calculate how long until the full amount of shares is unlocked
    remaining_time: uint256 = 0
    previously_locked_shares: uint256 = 0
    _full_profit_unlock_date: uint256 = self.full_profit_unlock_date
    if _full_profit_unlock_date > block.timestamp: 
      remaining_time = _full_profit_unlock_date - block.timestamp
      previously_locked_shares = self.balance_of[self] - newly_locked_shares

<<<<<<< HEAD
    # Vault insta unlocks losses and fees to avoid pps decrease
    # NOTE: it can only unlock shares that are previously locked. Any loss / fees over the amount of total locked shares will have an effect on pps
    shares_to_burn = min(shares_to_burn, previously_locked_shares + newly_locked_shares)
    if shares_to_burn > 0:
      self._burn_shares(shares_to_burn, self)
      # we burn first the newly locked shares, then the previously locked shares (the order in code is the inverse to save gas)
      previously_locked_shares -= (shares_to_burn - min(shares_to_burn, newly_locked_shares))
      newly_locked_shares -= min(shares_to_burn, newly_locked_shares)

    # Update unlocking rate and time to fully unlocked
    total_locked_shares: uint256 = previously_locked_shares + newly_locked_shares
    if total_locked_shares > 0:
      new_profit_locking_period: uint256 = (previously_locked_shares * remaining_time + newly_locked_shares * PROFIT_MAX_UNLOCK_TIME) / total_locked_shares
      self.profit_unlocking_rate = (previously_locked_shares + newly_locked_shares) * MAX_BPS / new_profit_locking_period
      self.full_profit_unlock_date = block.timestamp + new_profit_locking_period
      self.last_profit_update = block.timestamp
    else:
      # NOTE: only setting this to 0 will turn in the desired effect, no need to update last_profit_update or full_profit_unlock_date
      self.profit_unlocking_rate = 0
=======
    remaining_time: uint256 = 0
    _full_profit_unlock_date: uint256 = self.full_profit_unlock_date
    if _full_profit_unlock_date > block.timestamp: 
      remaining_time = _full_profit_unlock_date - block.timestamp
    else:
      remaining_time = 0

    previously_locked_shares: uint256 = remaining_time * self.profit_unlocking_rate

    shares_to_burn: uint256 = 0
    # Vault insta unlocks losses and fees to avoid pps decrease
    if loss + total_fees > 0:
        shares_to_unlock: uint256 = self._convert_to_shares(loss + total_fees)
        # TODO: second min needed to avoid reverts?
        shares_to_burn = min(shares_to_unlock, min(previously_locked_shares, self.balance_of[self]) + newly_locked_shares)
        self._burn_shares(shares_to_burn, self)
        if newly_locked_shares > shares_to_burn:
          newly_locked_shares -= shares_to_burn
        else:
          newly_locked_shares = 0
          # unlocking previously locked shares
          previously_locked_shares -= shares_to_burn - newly_locked_shares

    new_profit_locking_period: uint256 = (previously_locked_shares * remaining_time + newly_locked_shares * PROFIT_MAX_UNLOCK_TIME) / (previously_locked_shares + newly_locked_shares)

    self.profit_unlocking_rate = (previously_locked_shares + newly_locked_shares) * MAX_BPS / new_profit_locking_period
    self.full_profit_unlock_date = block.timestamp + new_profit_locking_period
    self.last_profit_update = block.timestamp

>>>>>>> 2b448a7 (feat: insta unlock losses and fees)

    self.strategies[strategy].last_report = block.timestamp
    log StrategyReported(
        strategy,
        gain,
        loss,
        self.strategies[strategy].current_debt,
        total_fees,
        total_refunds
    )
    return (gain, loss)


# SETTERS #
@external
def set_accountant(new_accountant: address):
    self._enforce_role(msg.sender, Roles.ACCOUNTING_MANAGER)
    self.accountant = new_accountant
    log UpdateAccountant(new_accountant)

@external
def set_deposit_limit(deposit_limit: uint256):
    self._enforce_role(msg.sender, Roles.ACCOUNTING_MANAGER)
    self.deposit_limit = deposit_limit
    log UpdateDepositLimit(deposit_limit)

@external
def set_minimum_total_idle(minimum_total_idle: uint256):
    self._enforce_role(msg.sender, Roles.DEBT_MANAGER)
    self.minimum_total_idle = minimum_total_idle
    log UpdateMinimumTotalIdle(minimum_total_idle)

# ROLE MANAGEMENT #
@internal
def _enforce_role(account: address, role: Roles):
    assert role in self.roles[account] or self.open_roles[role] # dev: not allowed

@external
def set_role(account: address, role: Roles):
    assert msg.sender == self.role_manager
    self.roles[account] = role

@external
def set_open_role(role: Roles):
    assert msg.sender == self.role_manager
    self.open_roles[role] = True

@external
def transfer_role_manager(role_manager: address):
    assert msg.sender == self.role_manager
    self.future_role_manager = role_manager

@external
def accept_role_manager():
    assert msg.sender == self.future_role_manager
    self.role_manager = msg.sender
    self.future_role_manager = empty(address)

# VAULT STATUS VIEWS
@view
@external
def price_per_share() -> uint256:
    return self._convert_to_assets(10 ** DECIMALS)

@view
@external
def available_deposit_limit() -> uint256:
    if self.deposit_limit > self._total_assets():
        return self.deposit_limit - self._total_assets()
    return 0

## ACCOUNTING MANAGEMENT ##
@external
def process_report(strategy: address) -> (uint256, uint256):
    self._enforce_role(msg.sender, Roles.ACCOUNTING_MANAGER)
    return self._process_report(strategy)

@external
def sweep(token: address) -> (uint256):
    self._enforce_role(msg.sender, Roles.ACCOUNTING_MANAGER)
    amount: uint256 = 0
    if token == ASSET.address:
        amount = ASSET.balanceOf(self) - self.total_idle
    else:
        amount = ERC20(token).balanceOf(self)
    assert amount != 0, "no dust"
    self.erc20_safe_transfer(ASSET.address, msg.sender, amount)
    log Sweep(token, amount)
    return amount

## STRATEGY MANAGEMENT ##
@external
def add_strategy(new_strategy: address):
    self._enforce_role(msg.sender, Roles.STRATEGY_MANAGER)
    self._add_strategy(new_strategy)

@external
def revoke_strategy(old_strategy: address):
    self._enforce_role(msg.sender, Roles.STRATEGY_MANAGER)
    self._revoke_strategy(old_strategy)

@external
def migrate_strategy(new_strategy: address, old_strategy: address):
    self._enforce_role(msg.sender, Roles.STRATEGY_MANAGER)
    self._migrate_strategy(new_strategy, old_strategy)

## DEBT MANAGEMENT ##
@external
def update_max_debt_for_strategy(strategy: address, new_max_debt: uint256):
    self._enforce_role(msg.sender, Roles.DEBT_MANAGER)
    assert self.strategies[strategy].activation != 0, "inactive strategy"
    self.strategies[strategy].max_debt = new_max_debt

    log UpdatedMaxDebtForStrategy(msg.sender, strategy, new_max_debt)

@external
def update_debt(strategy: address, target_debt: uint256) -> uint256:
    self._enforce_role(msg.sender, Roles.DEBT_MANAGER)
    return self._update_debt(strategy, target_debt)

## EMERGENCY MANAGEMENT ##
@external
def shutdown_vault():
    self._enforce_role(msg.sender, Roles.EMERGENCY_MANAGER)
    assert self.shutdown == False
    self.shutdown = True
    self.roles[msg.sender] = self.roles[msg.sender] | Roles.DEBT_MANAGER
    log Shutdown()


## SHARE MANAGEMENT ##
## ERC20 + ERC4626 ##
@external
def deposit(assets: uint256, receiver: address) -> uint256:
    return self._deposit(msg.sender, receiver, assets)

@external
def mint(shares: uint256, receiver: address) -> uint256:
    assets: uint256 = self._convert_to_assets(shares)
    self._deposit(msg.sender, receiver, assets)
    return assets

@external
def withdraw(assets: uint256, receiver: address, owner: address, strategies: DynArray[address, 10] = []) -> uint256:
    shares: uint256 = self._convert_to_shares(assets)
    self._redeem(msg.sender, receiver, owner, shares, strategies)
    return shares

@external
def redeem(shares: uint256, receiver: address, owner: address, strategies: DynArray[address, 10] = []) -> uint256:
    assets: uint256 = self._redeem(msg.sender, receiver, owner, shares, strategies)
    return assets

@external
def approve(spender: address, amount: uint256) -> bool:
    return self._approve(msg.sender, spender, amount)

@external
def transfer(receiver: address, amount: uint256) -> bool:
    assert receiver not in [self, empty(address)]
    self._transfer(msg.sender, receiver, amount)
    return True

@external
def transferFrom(sender: address, receiver: address, amount: uint256) -> bool:
    assert receiver not in [self, empty(address)]
    return self._transfer_from(sender, receiver, amount)

## ERC20+4626 compatibility
@external
def increaseAllowance(spender: address, amount: uint256) -> bool:
    return self._increase_allowance(msg.sender, spender, amount)

@external
def decreaseAllowance(spender: address, amount: uint256) -> bool:
    return self._decrease_allowance(msg.sender, spender, amount)

@external
def permit(owner: address, spender: address, amount: uint256, deadline: uint256, v: uint8, r: bytes32, s: bytes32) -> bool:
    return self._permit(owner, spender, amount, deadline, v, r, s)

@view
@external
def balanceOf(addr: address) -> uint256:
    if(addr == self):
      return self.balance_of[addr] - self._unlocked_shares()
    return self.balance_of[addr]

@view
@external
def totalSupply() -> uint256:
    return self._total_supply()

@view
@external
def asset() -> address:
    return ASSET.address

@view
@external
def decimals() -> uint256:
    return DECIMALS

@view
@external
def totalAssets() -> uint256:
    return self._total_assets()

@view
@external
def convertToShares(assets: uint256) -> uint256:
    return self._convert_to_shares(assets)

@view
@external
def previewDeposit(assets: uint256) -> uint256:
    return self._convert_to_shares(assets)

@view
@external
def previewMint(shares: uint256) -> uint256:
    return self._convert_to_assets(shares)

@view
@external
def convertToAssets(shares: uint256) -> uint256:
    return self._convert_to_assets(shares)

@view
@external
def maxDeposit(receiver: address) -> uint256:
    return self._max_deposit(receiver)

@view
@external
def maxMint(receiver: address) -> uint256:
    max_deposit: uint256 = self._max_deposit(receiver)
    return self._convert_to_shares(max_deposit)

@view
@external
def maxWithdraw(owner: address) -> uint256:
    # NOTE: as the withdraw function that complies with ERC4626 won't withdraw from strategies, this just uses liquidity available in the vault contract
    max_withdraw: uint256 = self._max_redeem(owner) # should be moved to a max_withdraw internal function
    return self._convert_to_assets(max_withdraw)

@view
@external
def maxRedeem(owner: address) -> uint256:
    # NOTE: as the withdraw function that complies with ERC4626 won't withdraw from strategies, this just uses liquidity available in the vault contract
    return self._max_redeem(owner)

@view
@external
def previewWithdraw(assets: uint256) -> uint256:
    return self._convert_to_shares(assets)

@view
@external
def previewRedeem(shares: uint256) -> uint256:
   return self._convert_to_assets(shares)

@view
@external
def api_version() -> String[28]:
    return API_VERSION

# eip-1344
@view
@internal
def domain_separator() -> bytes32:
    return keccak256(
        concat(
            DOMAIN_TYPE_HASH,
            keccak256(convert("Yearn Vault", Bytes[11])),
            keccak256(convert(API_VERSION, Bytes[28])),
            convert(chain.id, bytes32),
            convert(self, bytes32)
        )
    )

@view
@external
def DOMAIN_SEPARATOR() -> bytes32:
    return self.domain_separator()
