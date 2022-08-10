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
    total_gain: uint256
    total_loss: uint256
    total_fees: uint256

# DEBT MANAGEMENT EVENTS
event DebtUpdated:
    strategy: address
    current_debt: uint256
    new_debt: uint256

# STORAGE MANAGEMENT EVENTS
event UpdateFeeManager:
    fee_manager: address

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
    total_gain: uint256
    total_loss: uint256

# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000

# ENUMS #
enum Roles:
    STRATEGY_MANAGER
    DEBT_MANAGER
    EMERGENCY_MANAGER
    ACCOUNTING_MANAGER

# IMMUTABLE #
ASSET: immutable(ERC20)
DECIMALS: immutable(uint256)

# CONSTANTS #
API_VERSION: constant(String[28]) = "0.1.0"

# STORAGE #
strategies: public(HashMap[address, StrategyParams])
balance_of: HashMap[address, uint256]
allowance: public(HashMap[address, HashMap[address, uint256]])

total_supply: uint256
total_debt_: uint256
total_idle: public(uint256)
minimum_total_idle: public(uint256)
roles: public(HashMap[address, Roles])
deposit_limit: public(uint256)
fee_manager: public(address)
health_check: public(address)
role_manager: public(address)
future_role_manager: public(address)
shutdown: public(bool)

name: public(String[64])
symbol: public(String[32])

# `nonces` track `permit` approvals with signature.
nonces: public(HashMap[address, uint256])
DOMAIN_SEPARATOR: public(bytes32)
DOMAIN_TYPE_HASH: constant(bytes32) = keccak256('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
PERMIT_TYPE_HASH: constant(bytes32) = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)")

profit_end_date: public(uint256)  # Timestamp when profits are fully unlocked. Type uint256, as we are making comparison with block.timestamp (uint256)
profit_last_update: public(uint256)  # Last time buffer values were updated
profit_distribution_rate_: uint256  # Assets per second in which profits are being unlocked (assets/second)
PROFIT_MAX_UNLOCK_TIME: immutable(uint256)  # Max time profits need to be locked for (seconds) 

@external
def __init__(asset: ERC20, name: String[64], symbol: String[32], role_manager: address, profit_max_unlock_time: uint256):
    ASSET = asset
    DECIMALS = convert(ERC20Detailed(asset.address).decimals(), uint256)
    self.name = name
    self.symbol = symbol
    self.role_manager = role_manager
    # EIP-712
    self.DOMAIN_SEPARATOR = keccak256(
        concat(
            DOMAIN_TYPE_HASH,
            keccak256(convert("Yearn Vault", Bytes[11])),
            keccak256(convert(API_VERSION, Bytes[28])),
            convert(chain.id, bytes32),
            convert(self, bytes32)
        )
    )
    self.shutdown = False

    PROFIT_MAX_UNLOCK_TIME = profit_max_unlock_time
    self.profit_last_update = block.timestamp

## SHARE MANAGEMENT ##
## ERC20 ##
@internal
def _spend_allowance(owner: address, spender: address, amount: uint256):
    # Unlimited approval (saves an SSTORE)
    if (self.allowance[owner][spender] < MAX_UINT256):
        current_allowance: uint256 = self.allowance[owner][spender]
        assert current_allowance >= amount, "insufficient allowance"
        self.allowance[owner][spender] = current_allowance - amount
        # NOTE: Allows log filters to have a full accounting of allowance changes
        log Approval(owner, spender, current_allowance - amount)

@internal
def _transfer(sender: address, receiver: address, amount: uint256):
    # See note on `transfer()`.

    # Protect people from accidentally sending their shares to bad places
    assert receiver not in [self, ZERO_ADDRESS]
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
def _approve(spender: address, amount: uint256) -> bool:
    self.allowance[msg.sender][spender] = amount
    log Approval(msg.sender, spender, amount)
    return True

@internal
def _increase_allowance(spender: address, amount: uint256) -> bool:
    self.allowance[msg.sender][spender] += amount
    log Approval(msg.sender, spender, self.allowance[msg.sender][spender])
    return True

@internal
def _decrease_allowance(spender: address, amount: uint256) -> bool:
    self.allowance[msg.sender][spender] -= amount
    log Approval(msg.sender, spender, self.allowance[msg.sender][spender])
    return True

@internal
def _permit(owner: address, spender: address, amount: uint256, expiry: uint256, signature: Bytes[65]) -> bool:
    assert owner != ZERO_ADDRESS, "invalid owner"
    assert expiry == 0 or expiry >= block.timestamp, "permit expired"
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
    assert ecrecover(digest, v, r, s) == owner, "invalid signature"
    self.allowance[owner][spender] = amount
    self.nonces[owner] = nonce + 1
    log Approval(owner, spender, amount)
    return True

@view
@internal
def _total_assets() -> uint256:
    return self.total_idle + self._total_debt()

@internal
def _burn_shares(shares: uint256, owner: address):
    self.balance_of[owner] -= shares
    self.total_supply -= shares

@view
@internal
def _convert_to_assets(shares: uint256) -> uint256:
    _total_supply: uint256 = self.total_supply
    amount: uint256 = shares
    if _total_supply > 0:
        amount = shares * self._total_assets() / self.total_supply
    return amount

@view
@internal
def _convert_to_shares(amount: uint256) -> uint256:
    _total_supply: uint256 = self.total_supply
    shares: uint256 = amount
    if _total_supply > 0:
        shares = amount * _total_supply / self._total_assets()
    return shares


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
    new_shares: uint256 = self._convert_to_shares(amount)
    assert new_shares > 0

    self.balance_of[recipient] += new_shares
    self.total_supply += new_shares

    # TODO: emit event
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
    return min(self.balance_of[owner], self._convert_to_shares(self.total_idle))


@internal
def _deposit(_sender: address, _recipient: address, _assets: uint256) -> uint256:
    assert self.shutdown == False # dev: shutdown
    assert _recipient not in [self, ZERO_ADDRESS], "invalid recipient"
    assets: uint256 = _assets

    if assets == MAX_UINT256:
        assets = ASSET.balanceOf(_sender)

    assert self._total_assets() + assets <= self.deposit_limit, "exceed deposit limit"
    assert assets > 0, "cannot deposit zero"

    shares: uint256 = self._issue_shares_for_amount(assets, _recipient)

    self.erc20_safe_transfer_from(ASSET.address, msg.sender, self, assets)
    self.total_idle += assets

    log Deposit(_sender, _recipient, assets, shares)

    return shares

@internal
def _redeem(sender: address, receiver: address, owner: address, shares_to_burn: uint256, strategies: DynArray[address, 10] = []) -> uint256:
    if sender != owner:
        self._spend_allowance(owner, sender, shares_to_burn)

    shares: uint256 = shares_to_burn
    shares_balance: uint256 = self.balance_of[owner]

    if shares == MAX_UINT256:
        shares = shares_balance

    assert shares_balance >= shares, "insufficient shares to withdraw"
    assert shares > 0, "no shares to withdraw"

    assets: uint256 = self._convert_to_assets(shares)

    # load to memory to save gas
    curr_total_idle: uint256 = self.total_idle

    if assets > curr_total_idle:
        # load to memory to save gas
        curr_total_debt: uint256 = self.total_debt_

        # withdraw from strategies if insufficient total idle
        assets_needed: uint256 = assets - curr_total_idle
        assets_to_withdraw: uint256 = 0
        for strategy in strategies:
            assert self.strategies[strategy].activation != 0, "inactive strategy"

            assets_to_withdraw = min(assets_needed, IStrategy(strategy).withdrawable())
            # continue if nothing to withdraw
            if assets_to_withdraw == 0:
                continue

	    # TODO: should the vault check that the strategy has unlocked requested funds?
	    # if so, should it just withdraw the unlocked funds and just assume the rest are lost?
            IStrategy(strategy).freeFunds(assets_to_withdraw)
            ASSET.transferFrom(strategy, self, assets_to_withdraw)
            curr_total_idle += assets_to_withdraw
            curr_total_debt -= assets_to_withdraw
            self.strategies[strategy].current_debt -= assets_to_withdraw

            # break if we have enough total idle
            if assets <= curr_total_idle:
                break

            assets_needed -= assets_to_withdraw

        # if we exhaust the queue and still have insufficient total idle, revert
        assert curr_total_idle >= assets, "insufficient total idle"
        # commit memory to storage
        self.total_debt_ = curr_total_debt

    self._burn_shares(shares, owner)
    self.total_idle = curr_total_idle - assets
    self.erc20_safe_transfer(ASSET.address, receiver, assets)

    log Withdraw(sender, receiver, owner, assets, shares)

    return assets

## STRATEGY MANAGEMENT ##
@internal
def _add_strategy(new_strategy: address):
   assert new_strategy != ZERO_ADDRESS, "strategy cannot be zero address"
   assert IStrategy(new_strategy).asset() == ASSET.address, "invalid asset"
   assert IStrategy(new_strategy).vault() == self, "invalid vault"
   assert self.strategies[new_strategy].activation == 0, "strategy already active"

   self.strategies[new_strategy] = StrategyParams({
      activation: block.timestamp,
      last_report: block.timestamp,
      current_debt: 0,
      max_debt: 0,
      total_gain: 0,
      total_loss: 0
   })

   log StrategyAdded(new_strategy)

@internal
def _revoke_strategy(old_strategy: address):
   assert self.strategies[old_strategy].activation != 0, "strategy not active"
   # NOTE: strategy needs to have 0 debt to be revoked
   assert self.strategies[old_strategy].current_debt == 0, "strategy has debt"

   # NOTE: strategy params are set to 0 (warning: it can be readded)
   self.strategies[old_strategy] = StrategyParams({
      activation: 0,
      last_report: 0,
      current_debt: 0,
      max_debt: 0,
      total_gain: 0,
      total_loss: 0
   })

   log StrategyRevoked(old_strategy)

@internal
def _migrate_strategy(new_strategy: address, old_strategy: address):
    assert self.strategies[old_strategy].activation != 0, "old strategy not active"
    assert self.strategies[old_strategy].current_debt == 0, "old strategy has debt"
    assert new_strategy != ZERO_ADDRESS, "strategy cannot be zero address"
    assert IStrategy(new_strategy).asset() == ASSET.address, "invalid asset"
    assert IStrategy(new_strategy).vault() == self, "invalid vault"
    assert self.strategies[new_strategy].activation == 0, "strategy already active"

    migrated_strategy: StrategyParams = self.strategies[old_strategy]

    # NOTE: we add strategy with same params than the strategy being migrated
    self.strategies[new_strategy] = StrategyParams({
       activation: block.timestamp,
       last_report: block.timestamp,
       current_debt: migrated_strategy.current_debt,
       max_debt: migrated_strategy.max_debt,
       total_gain: 0,
       total_loss: 0
    })

    self._revoke_strategy(old_strategy)

    log StrategyMigrated(old_strategy, new_strategy)

# DEBT MANAGEMENT #
@internal
def _update_debt(strategy: address) -> uint256:
    self._enforce_role(msg.sender, Roles.DEBT_MANAGER)
    current_debt: uint256 = self.strategies[strategy].current_debt

    min_desired_debt: uint256 = 0
    max_desired_debt: uint256 = 0
    min_desired_debt, max_desired_debt = IStrategy(strategy).investable()

    new_debt: uint256 = self.strategies[strategy].max_debt

    if self.shutdown:
        new_debt = 0

    if new_debt > current_debt:
        # only check if debt is increasing
        # if debt is decreasing, we ignore strategy min debt
        assert (new_debt >= min_desired_debt), "new debt less than min debt"

    if new_debt > max_desired_debt:
        new_debt = max_desired_debt

    assert new_debt != current_debt, "new debt equals current debt"

    if current_debt > new_debt:
        # reduce debt
        assets_to_withdraw: uint256 = current_debt - new_debt

        # ensure we always have minimum_total_idle when updating debt
        # HACK: to save gas
        minimum_total_idle: uint256 = self.minimum_total_idle
        total_idle: uint256 = self.total_idle

        if total_idle + assets_to_withdraw < minimum_total_idle:
            assets_to_withdraw = minimum_total_idle - total_idle
            if assets_to_withdraw > current_debt:
                assets_to_withdraw = current_debt
            new_debt = current_debt - assets_to_withdraw

        withdrawable: uint256 = IStrategy(strategy).withdrawable()
        assert withdrawable != 0, "nothing to withdraw"

        # if insufficient withdrawable, withdraw what we can
        if (withdrawable < assets_to_withdraw):
            assets_to_withdraw = withdrawable
            new_debt = current_debt - withdrawable

        IStrategy(strategy).freeFunds(assets_to_withdraw)
	# TODO: is it worth it to transfer the max_amount between assets_to_withdraw and balance?
        ASSET.transferFrom(strategy, self, assets_to_withdraw)
        self.total_idle += assets_to_withdraw
        self.total_debt_ -= assets_to_withdraw
    else:
        # increase debt
        assets_to_transfer: uint256 = new_debt - current_debt
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
            ASSET.transfer(strategy, assets_to_transfer)
            self.total_idle -= assets_to_transfer
            self.total_debt_ += assets_to_transfer

    self.strategies[strategy].current_debt = new_debt

    log DebtUpdated(strategy, current_debt, new_debt)
    return new_debt

## ACCOUNTING MANAGEMENT ##

@internal
def _process_report(strategy: address) -> (uint256, uint256):
    assert self.strategies[strategy].activation != 0, "inactive strategy"
    total_assets: uint256 = IStrategy(strategy).totalAssets()
    current_debt: uint256 = self.strategies[strategy].current_debt
    assert total_assets != current_debt, "nothing to report"

    gain: uint256 = 0
    loss: uint256 = 0

    # TODO: implement health check

    if total_assets > current_debt:
        gain = total_assets - current_debt
    else:
        loss = current_debt - total_assets

    # We compute unlocked_profit and aux vars for profit locking
    remaining_time: uint256 = 0
    unlocked_profit: uint256 = 0 
    pending_profit: uint256 = 0
    profit_distribution_rate_: uint256 = self.profit_distribution_rate_
    if profit_distribution_rate_ != 0:
        profit_end_date: uint256 = self.profit_end_date
        if block.timestamp > profit_end_date:
            unlocked_profit = (profit_end_date - self.profit_last_update) * profit_distribution_rate_ / MAX_BPS
            self.profit_distribution_rate_ = 0
        else:
            unlocked_profit = (block.timestamp - self.profit_last_update) * profit_distribution_rate_ / MAX_BPS
            remaining_time = profit_end_date - block.timestamp
            pending_profit = profit_distribution_rate_ * remaining_time / MAX_BPS

    if loss > 0:
        self.strategies[strategy].total_loss += loss
        self.strategies[strategy].current_debt -= loss

        if loss >= pending_profit:
            # If loss is too big for the profit buffer, we set distribution rate to zero
            self.total_debt_ = self.total_debt_ + unlocked_profit - (loss - pending_profit) 
            self.profit_distribution_rate_ = 0
        else:
            self.profit_distribution_rate_ = (pending_profit - loss) * MAX_BPS / remaining_time
            self.total_debt_ += unlocked_profit
            self.profit_last_update = block.timestamp

            
            self.total_debt -= loss

    total_fees: uint256 = 0
    if gain > 0:
        fee_manager: address = self.fee_manager
        # if fee manager is not set, fees are zero
        if fee_manager != ZERO_ADDRESS:
            total_fees = IFeeManager(fee_manager).assess_fees(strategy, gain)
            # if fees are non-zero, issue shares
            if total_fees > 0:
                self._issue_shares_for_amount(total_fees, fee_manager)

        # gains are always realized pnl (i.e. not upnl)
        self.strategies[strategy].total_gain += gain
        # update current debt after processing management fee
        self.strategies[strategy].current_debt += gain


        if PROFIT_MAX_UNLOCK_TIME == 0:
            self.total_debt_ += gain + unlocked_profit
        else:
            if total_fees < gain:
                gain_without_fees: uint256 = gain - total_fees       
                # The new locking period is the weighted average between the remaining time and the profit_max_unlock_time. 
                # The weight used is the profit (pending_profit vs new_profit)
                new_profit_locking_period:uint256 = (pending_profit * remaining_time + gain_without_fees * PROFIT_MAX_UNLOCK_TIME) / (pending_profit + gain_without_fees)
                self.profit_distribution_rate_ = (pending_profit + gain_without_fees) * MAX_BPS / new_profit_locking_period
                self.profit_end_date =  block.timestamp + new_profit_locking_period
                self.profit_last_update = block.timestamp
                self.total_debt_ += unlocked_profit + total_fees
            else:
                if total_fees - gain < pending_profit :
                    # If there is pending profit, we reduce it by the difference between total_fees and gain
                    self.profit_distribution_rate_ = (pending_profit - (total_fees - gain)) * MAX_BPS / remaining_time
                    self.profit_end_date =  block.timestamp + remaining_time
                    self.profit_last_update = block.timestamp
                    self.total_debt_ += unlocked_profit + total_fees
                else:
                    # If even pending profit is not enough. 
                    # We don´t add whole total_fees to total_debt, as there is not enough, we only add what we can pay, else is repercuted on pps
                    self.profit_distribution_rate_ = 0
                    self.total_debt_ += unlocked_profit + gain + pending_profit

    
    self.strategies[strategy].last_report = block.timestamp

    strategy_params: StrategyParams = self.strategies[strategy]
    log StrategyReported(
        strategy,
        gain,
        loss,
        strategy_params.current_debt,
        strategy_params.total_gain,
        strategy_params.total_loss,
        total_fees
    )
    return (gain, loss)    

@view
@internal
def _compute_unlocked_profit() -> uint256:
    """
    If profit_distribution_rate is equal to zero, there is no profit to unlock, otherwise we compute it
    """
    profit_distribution_rate: uint256 = self.profit_distribution_rate_
    if profit_distribution_rate != 0:
        # Not caching `profit_end_date` as positive scenario should be a lot more common, and would add 6 gas each time
        if self.profit_end_date >= block.timestamp:
            return (block.timestamp - self.profit_last_update) * profit_distribution_rate / MAX_BPS
        else:
            return (self.profit_end_date - self.profit_last_update) * profit_distribution_rate / MAX_BPS
    return 0

@view
@internal
def _total_debt() -> uint256:
    return self.total_debt_ + self._compute_unlocked_profit()


@view
@internal
def _profit_distribution_rate() -> uint256:
    if self.profit_end_date >= block.timestamp:
        return self.profit_distribution_rate_
    # If we are past profit_end_date, it means profit is fully unlocked (rate=0) but we haven´t yet updated state on contract
    return 0



# # EMERGENCY FUNCTIONS #
# def set_emergency_shutdown(emergency: bool):
#     # permissioned: EMERGENCY_MANAGER
#     # TODO: change emergency shutdown flag
#     return

# SETTERS #
@external
def set_fee_manager(new_fee_manager: address):
    # TODO: permissioning: CONFIG_MANAGER
    self.fee_manager = new_fee_manager
    log UpdateFeeManager(new_fee_manager)

@external
def set_deposit_limit(deposit_limit: uint256):
    # TODO: permissioning: CONFIG_MANAGER
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
    assert role in self.roles[account] # dev: not allowed

@external
def set_role(account: address, role: Roles):
    assert msg.sender == self.role_manager
    self.roles[account] = role

@external
def transfer_role_manager(role_manager: address):
    assert msg.sender == self.role_manager
    self.future_role_manager = role_manager

@external
def accept_role_manager():
    assert msg.sender == self.future_role_manager
    self.role_manager = msg.sender
    self.future_role_manager = ZERO_ADDRESS

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
    # TODO: should it be open?
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
    ERC20(token).transfer(msg.sender, amount)
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
    # TODO: should we check that total_max_debt is not over 100% of assets?
    self.strategies[strategy].max_debt = new_max_debt

    log UpdatedMaxDebtForStrategy(msg.sender, strategy, new_max_debt)

@external
def update_debt(strategy: address) -> uint256:
    return self._update_debt(strategy)

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
    # TODO: withdrawal queue is empty here. Do we need to implement a custom withdrawal queue?
    self._redeem(msg.sender, receiver, owner, shares, strategies)
    return shares

@external
def redeem(shares: uint256, receiver: address, owner: address, strategies: DynArray[address, 10] = []) -> uint256:
    assets: uint256 = self._redeem(msg.sender, receiver, owner, shares, strategies)
    return assets

@external
def approve(spender: address, amount: uint256) -> bool:
    return self._approve(spender, amount)

@external
def transfer(receiver: address, amount: uint256) -> bool:
    self._transfer(msg.sender, receiver, amount)
    return True

## EMERGENCY MANAGEMENT ##
@external
def shutdown_vault():
    self._enforce_role(msg.sender, Roles.EMERGENCY_MANAGER)
    assert self.shutdown == False
    self.shutdown = True
    self.roles[msg.sender] = self.roles[msg.sender] | Roles.DEBT_MANAGER
    log Shutdown()

## ERC20+4626 compatibility
@external
def transferFrom(sender: address, receiver: address, amount: uint256) -> bool:
    return self._transfer_from(sender, receiver, amount)

@external
def increaseAllowance(spender: address, amount: uint256) -> bool:
    return self._increase_allowance(spender, amount)

@external
def decreaseAllowance(spender: address, amount: uint256) -> bool:
    return self._decrease_allowance(spender, amount)

@external
def permit(owner: address, spender: address, amount: uint256, expiry: uint256, signature: Bytes[65]) -> bool:
    return self._permit(owner, spender, amount, expiry, signature)

@view
@external
def balanceOf(addr: address) -> uint256:
    return self.balance_of[addr]

@view
@external
def totalSupply() -> uint256:
    return self.total_supply

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
def total_debt() -> uint256:
    return self._total_debt()

@view
@external
def profit_distribution_rate() -> uint256:
    return self._profit_distribution_rate()

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
    # TODO: calculate max between liquidity
    # TODO: take this into account when implementing withdrawing from custom strategies
    max_withdraw: uint256 = self._max_redeem(owner) # should be moved to a max_withdraw internal function
    return self._convert_to_assets(max_withdraw)

@view
@external
def maxRedeem(owner: address) -> uint256:
    # TODO: add max liquidity calculation
    # TODO: take this into account when implementing withdrawing from custom strategies
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
