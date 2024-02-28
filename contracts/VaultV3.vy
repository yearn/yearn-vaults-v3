# @version 0.3.7

"""
@title Yearn V3 Vault
@license GNU AGPLv3
@author yearn.finance
@notice
    The Yearn VaultV3 is designed as a non-opinionated system to distribute funds of 
    depositors for a specific `asset` into different opportunities (aka Strategies)
    and manage accounting in a robust way.

    Depositors receive shares (aka vaults tokens) proportional to their deposit amount. 
    Vault tokens are yield-bearing and can be redeemed at any time to get back deposit 
    plus any yield generated.

    Addresses that are given different permissioned roles by the `role_manager` 
    are then able to allocate funds as they best see fit to different strategies 
    and adjust the strategies and allocations as needed, as well as reporting realized
    profits or losses.

    Strategies are any ERC-4626 compliant contracts that use the same underlying `asset` 
    as the vault. The vault provides no assurances as to the safety of any strategy
    and it is the responsibility of those that hold the corresponding roles to choose
    and fund strategies that best fit their desired specifications.

    Those holding vault tokens are able to redeem the tokens for the corresponding
    amount of underlying asset based on any reported profits or losses since their
    initial deposit.

    The vault is built to be customized by the management to be able to fit their
    specific desired needs. Including the customization of strategies, accountants, 
    ownership etc.
"""

# INTERFACES #

from vyper.interfaces import ERC20
from vyper.interfaces import ERC20Detailed

interface IStrategy:
    def asset() -> address: view
    def balanceOf(owner: address) -> uint256: view
    def convertToAssets(shares: uint256) -> uint256: view
    def convertToShares(assets: uint256) -> uint256: view
    def previewWithdraw(assets: uint256) -> uint256: view
    def maxDeposit(receiver: address) -> uint256: view
    def deposit(assets: uint256, receiver: address) -> uint256: nonpayable
    def maxRedeem(owner: address) -> uint256: view
    def redeem(shares: uint256, receiver: address, owner: address) -> uint256: nonpayable
    
interface IAccountant:
    def report(strategy: address, gain: uint256, loss: uint256) -> (uint256, uint256): nonpayable

interface IDepositLimitModule:
    def available_deposit_limit(receiver: address) -> uint256: view
    
interface IWithdrawLimitModule:
    def available_withdraw_limit(owner: address, max_loss: uint256, strategies: DynArray[address, MAX_QUEUE]) -> uint256: view

interface IFactory:
    def protocol_fee_config() -> (uint16, address): view

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

# STRATEGY EVENTS
event StrategyChanged:
    strategy: indexed(address)
    change_type: indexed(StrategyChangeType)
    
event StrategyReported:
    strategy: indexed(address)
    gain: uint256
    loss: uint256
    current_debt: uint256
    protocol_fees: uint256
    total_fees: uint256
    total_refunds: uint256

# DEBT MANAGEMENT EVENTS
event DebtUpdated:
    strategy: indexed(address)
    current_debt: uint256
    new_debt: uint256

# ROLE UPDATES
event RoleSet:
    account: indexed(address)
    role: indexed(Roles)

# STORAGE MANAGEMENT EVENTS
event UpdateRoleManager:
    role_manager: indexed(address)

event UpdateAccountant:
    accountant: indexed(address)

event UpdateDepositLimitModule:
    deposit_limit_module: indexed(address)

event UpdateWithdrawLimitModule:
    withdraw_limit_module: indexed(address)

event UpdateDefaultQueue:
    new_default_queue: DynArray[address, MAX_QUEUE]

event UpdateUseDefaultQueue:
    use_default_queue: bool

event UpdatedMaxDebtForStrategy:
    sender: indexed(address)
    strategy: indexed(address)
    new_debt: uint256

event UpdateDepositLimit:
    deposit_limit: uint256

event UpdateMinimumTotalIdle:
    minimum_total_idle: uint256

event UpdateProfitMaxUnlockTime:
    profit_max_unlock_time: uint256

event DebtPurchased:
    strategy: indexed(address)
    amount: uint256

event Shutdown:
    pass

# STRUCTS #
struct StrategyParams:
    # Timestamp when the strategy was added.
    activation: uint256 
    # Timestamp of the strategies last report.
    last_report: uint256
    # The current assets the strategy holds.
    current_debt: uint256
    # The max assets the strategy can hold. 
    max_debt: uint256

# CONSTANTS #
# The max length the withdrawal queue can be.
MAX_QUEUE: constant(uint256) = 10
# 100% in Basis Points.
MAX_BPS: constant(uint256) = 10_000
# Extended for profit locking calculations.
MAX_BPS_EXTENDED: constant(uint256) = 1_000_000_000_000
# The version of this vault.
API_VERSION: constant(String[28]) = "3.0.2"

# ENUMS #
# Each permissioned function has its own Role.
# Roles can be combined in any combination or all kept separate.
# Follows python Enum patterns so the first Enum == 1 and doubles each time.
enum Roles:
    ADD_STRATEGY_MANAGER # Can add strategies to the vault.
    REVOKE_STRATEGY_MANAGER # Can remove strategies from the vault.
    FORCE_REVOKE_MANAGER # Can force remove a strategy causing a loss.
    ACCOUNTANT_MANAGER # Can set the accountant that assess fees.
    QUEUE_MANAGER # Can set the default withdrawal queue.
    REPORTING_MANAGER # Calls report for strategies.
    DEBT_MANAGER # Adds and removes debt from strategies.
    MAX_DEBT_MANAGER # Can set the max debt for a strategy.
    DEPOSIT_LIMIT_MANAGER # Sets deposit limit and module for the vault.
    WITHDRAW_LIMIT_MANAGER # Sets the withdraw limit module.
    MINIMUM_IDLE_MANAGER # Sets the minimum total idle the vault should keep.
    PROFIT_UNLOCK_MANAGER # Sets the profit_max_unlock_time.
    DEBT_PURCHASER # Can purchase bad debt from the vault.
    EMERGENCY_MANAGER # Can shutdown vault in an emergency.

enum StrategyChangeType:
    ADDED
    REVOKED

enum Rounding:
    ROUND_DOWN
    ROUND_UP

# STORAGE #
# Underlying token used by the vault.
asset: public(address)
# Based off the `asset` decimals.
decimals: public(uint8)
# Deployer contract used to retrieve the protocol fee config.
factory: address

# HashMap that records all the strategies that are allowed to receive assets from the vault.
strategies: public(HashMap[address, StrategyParams])
# The current default withdrawal queue.
default_queue: public(DynArray[address, MAX_QUEUE])
# Should the vault use the default_queue regardless whats passed in.
use_default_queue: public(bool)

### ACCOUNTING ###
# ERC20 - amount of shares per account
balance_of: HashMap[address, uint256]
# ERC20 - owner -> (spender -> amount)
allowance: public(HashMap[address, HashMap[address, uint256]])
# Total amount of shares that are currently minted including those locked.
total_supply: uint256
# Total amount of assets that has been deposited in strategies.
total_debt: uint256
# Current assets held in the vault contract. Replacing balanceOf(this) to avoid price_per_share manipulation.
total_idle: uint256
# Minimum amount of assets that should be kept in the vault contract to allow for fast, cheap redeems.
minimum_total_idle: public(uint256)
# Maximum amount of tokens that the vault can accept. If totalAssets > deposit_limit, deposits will revert.
deposit_limit: public(uint256)

### PERIPHERY ###
# Contract that charges fees and can give refunds.
accountant: public(address)
# Contract to control the deposit limit.
deposit_limit_module: public(address)
# Contract to control the withdraw limit.
withdraw_limit_module: public(address)

### ROLES ###
# HashMap mapping addresses to their roles
roles: public(HashMap[address, Roles])
# Address that can add and remove roles to addresses.
role_manager: public(address)
# Temporary variable to store the address of the next role_manager until the role is accepted.
future_role_manager: public(address)

# ERC20 - name of the vaults token.
name: public(String[64])
# ERC20 - symbol of the vaults token.
symbol: public(String[32])

# State of the vault - if set to true, only withdrawals will be available. It can't be reverted.
shutdown: bool
# The amount of time profits will unlock over.
profit_max_unlock_time: uint256
# The timestamp of when the current unlocking period ends.
full_profit_unlock_date: uint256
# The per second rate at which profit will unlock.
profit_unlocking_rate: uint256
# Last timestamp of the most recent profitable report.
last_profit_update: uint256

# `nonces` track `permit` approvals with signature.
nonces: public(HashMap[address, uint256])
DOMAIN_TYPE_HASH: constant(bytes32) = keccak256('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
PERMIT_TYPE_HASH: constant(bytes32) = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)")

# Constructor
@external
def __init__():
    # Set `asset` so it cannot be re-initialized.
    self.asset = self
    
@external
def initialize(
    asset: address, 
    name: String[64], 
    symbol: String[32], 
    role_manager: address, 
    profit_max_unlock_time: uint256
):
    """
    @notice
        Initialize a new vault. Sets the asset, name, symbol, and role manager.
    @param asset
        The address of the asset that the vault will accept.
    @param name
        The name of the vault token.
    @param symbol
        The symbol of the vault token.
    @param role_manager 
        The address that can add and remove roles to addresses
    @param profit_max_unlock_time
        The amount of time that the profit will be locked for
    """
    assert self.asset == empty(address), "initialized"
    assert asset != empty(address), "ZERO ADDRESS"
    assert role_manager != empty(address), "ZERO ADDRESS"

    self.asset = asset
    # Get the decimals for the vault to use.
    self.decimals = ERC20Detailed(asset).decimals()
    
    # Set the factory as the deployer address.
    self.factory = msg.sender

    # Must be less than one year for report cycles
    assert profit_max_unlock_time <= 31_556_952 # dev: profit unlock time too long
    self.profit_max_unlock_time = profit_max_unlock_time

    self.name = name
    self.symbol = symbol
    self.role_manager = role_manager

## SHARE MANAGEMENT ##
## ERC20 ##
@internal
def _spend_allowance(owner: address, spender: address, amount: uint256):
    # Unlimited approval does nothing (saves an SSTORE)
    current_allowance: uint256 = self.allowance[owner][spender]
    if (current_allowance < max_value(uint256)):
        assert current_allowance >= amount, "insufficient allowance"
        self._approve(owner, spender, unsafe_sub(current_allowance, amount))

@internal
def _transfer(sender: address, receiver: address, amount: uint256):
    sender_balance: uint256 = self.balance_of[sender]
    assert sender_balance >= amount, "insufficient funds"
    self.balance_of[sender] = unsafe_sub(sender_balance, amount)
    self.balance_of[receiver] = unsafe_add(self.balance_of[receiver], amount)
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
def _permit(
    owner: address, 
    spender: address, 
    amount: uint256, 
    deadline: uint256, 
    v: uint8, 
    r: bytes32, 
    s: bytes32
) -> bool:
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
    assert ecrecover(
        digest, v, r, s
    ) == owner, "invalid signature"

    self.allowance[owner][spender] = amount
    self.nonces[owner] = nonce + 1
    log Approval(owner, spender, amount)
    return True

@internal
def _burn_shares(shares: uint256, owner: address):
    self.balance_of[owner] -= shares
    self.total_supply = unsafe_sub(self.total_supply, shares)
    log Transfer(owner, empty(address), shares)

@view
@internal
def _unlocked_shares() -> uint256:
    """
    Returns the amount of shares that have been unlocked.
    To avoid sudden price_per_share spikes, profits can be processed 
    through an unlocking period. The mechanism involves shares to be 
    minted to the vault which are unlocked gradually over time. Shares 
    that have been locked are gradually unlocked over profit_max_unlock_time.
    """
    _full_profit_unlock_date: uint256 = self.full_profit_unlock_date
    unlocked_shares: uint256 = 0
    if _full_profit_unlock_date > block.timestamp:
        # If we have not fully unlocked, we need to calculate how much has been.
        unlocked_shares = self.profit_unlocking_rate * (block.timestamp - self.last_profit_update) / MAX_BPS_EXTENDED

    elif _full_profit_unlock_date != 0:
        # All shares have been unlocked
        unlocked_shares = self.balance_of[self]

    return unlocked_shares


@view
@internal
def _total_supply() -> uint256:
    # Need to account for the shares issued to the vault that have unlocked.
    return self.total_supply - self._unlocked_shares()

@view
@internal
def _total_assets() -> uint256:
    """
    Total amount of assets that are in the vault and in the strategies. 
    """
    return self.total_idle + self.total_debt

@view
@internal
def _convert_to_assets(shares: uint256, rounding: Rounding) -> uint256:
    """ 
    assets = shares * (total_assets / total_supply) --- (== price_per_share * shares)
    """
    if shares == max_value(uint256) or shares == 0:
        return shares

    total_supply: uint256 = self._total_supply()
    # if total_supply is 0, price_per_share is 1
    if total_supply == 0: 
        return shares

    numerator: uint256 = shares * self._total_assets()
    amount: uint256 = numerator / total_supply
    if rounding == Rounding.ROUND_UP and numerator % total_supply != 0:
        amount += 1

    return amount

@view
@internal
def _convert_to_shares(assets: uint256, rounding: Rounding) -> uint256:
    """
    shares = amount * (total_supply / total_assets) --- (== amount / price_per_share)
    """
    if assets == max_value(uint256) or assets == 0:
        return assets

    total_supply: uint256 = self._total_supply()
    total_assets: uint256 = self._total_assets()

    if total_assets == 0:
        # if total_assets and total_supply is 0, price_per_share is 1
        if total_supply == 0:
            return assets
        else:
            # Else if total_supply > 0 price_per_share is 0
            return 0

    numerator: uint256 = assets * total_supply
    shares: uint256 = numerator / total_assets
    if rounding == Rounding.ROUND_UP and numerator % total_assets != 0:
        shares += 1

    return shares

@internal
def _erc20_safe_approve(token: address, spender: address, amount: uint256):
    # Used only to approve tokens that are not the type managed by this Vault.
    # Used to handle non-compliant tokens like USDT
    assert ERC20(token).approve(spender, amount, default_return_value=True), "approval failed"

@internal
def _erc20_safe_transfer_from(token: address, sender: address, receiver: address, amount: uint256):
    # Used only to transfer tokens that are not the type managed by this Vault.
    # Used to handle non-compliant tokens like USDT
    assert ERC20(token).transferFrom(sender, receiver, amount, default_return_value=True), "transfer failed"

@internal
def _erc20_safe_transfer(token: address, receiver: address, amount: uint256):
    # Used only to send tokens that are not the type managed by this Vault.
    # Used to handle non-compliant tokens like USDT
    assert ERC20(token).transfer(receiver, amount, default_return_value=True), "transfer failed"

@internal
def _issue_shares(shares: uint256, recipient: address):
    self.balance_of[recipient] = unsafe_add(self.balance_of[recipient], shares)
    self.total_supply += shares

    log Transfer(empty(address), recipient, shares)

@internal
def _issue_shares_for_amount(amount: uint256, recipient: address) -> uint256:
    """
    Issues shares that are worth 'amount' in the underlying token (asset).
    WARNING: this takes into account that any new assets have been summed 
    to total_assets (otherwise pps will go down).
    """
    total_supply: uint256 = self._total_supply()
    total_assets: uint256 = self._total_assets()
    new_shares: uint256 = 0
    
    # If no supply PPS = 1.
    if total_supply == 0:
        new_shares = amount
    elif total_assets > amount:
        new_shares = amount * total_supply / (total_assets - amount)

    # We don't make the function revert
    if new_shares == 0:
       return 0

    self._issue_shares(new_shares, recipient)

    return new_shares

## ERC4626 ##
@view
@internal
def _max_deposit(receiver: address) -> uint256: 
    if receiver in [empty(address), self]:
        return 0

    # If there is a deposit limit module set use that.
    deposit_limit_module: address = self.deposit_limit_module
    if deposit_limit_module != empty(address):
        return IDepositLimitModule(deposit_limit_module).available_deposit_limit(receiver)
    
    # Else use the standard flow.
    _deposit_limit: uint256 = self.deposit_limit
    if (_deposit_limit == max_value(uint256)):
        return _deposit_limit

    _total_assets: uint256 = self._total_assets()
    if (_total_assets >= _deposit_limit):
        return 0

    return unsafe_sub(_deposit_limit, _total_assets)

@view
@internal
def _max_withdraw(
    owner: address,
    max_loss: uint256,
    strategies: DynArray[address, MAX_QUEUE]
) -> uint256:
    """
    @dev Returns the max amount of `asset` an `owner` can withdraw.

    This will do a full simulation of the withdraw in order to determine
    how much is currently liquid and if the `max_loss` would allow for the 
    tx to not revert.

    This will track any expected loss to check if the tx will revert, but
    not account for it in the amount returned since it is unrealised and 
    therefore will not be accounted for in the conversion rates.

    i.e. If we have 100 debt and 10 of unrealised loss, the max we can get
    out is 90, but a user of the vault will need to call withdraw with 100
    in order to get the full 90 out.
    """

    # Get the max amount for the owner if fully liquid.
    max_assets: uint256 = self._convert_to_assets(self.balance_of[owner], Rounding.ROUND_DOWN)

    # If there is a withdraw limit module use that.
    withdraw_limit_module: address = self.withdraw_limit_module
    if withdraw_limit_module != empty(address):
        return min(
            # Use the min between the returned value and the max.
            # Means the limit module doesn't need to account for balances or conversions.
            IWithdrawLimitModule(withdraw_limit_module).available_withdraw_limit(owner, max_loss, strategies),
            max_assets
        )
    
    # See if we have enough idle to service the withdraw.
    current_idle: uint256 = self.total_idle
    if max_assets > current_idle:
        # Track how much we can pull.
        have: uint256 = current_idle
        loss: uint256 = 0

        # Cache the default queue.
        _strategies: DynArray[address, MAX_QUEUE] = self.default_queue

        # If a custom queue was passed, and we don't force the default queue.
        if len(strategies) != 0 and not self.use_default_queue:
            # Use the custom queue.
            _strategies = strategies

        for strategy in _strategies:
            # Can't use an invalid strategy.
            assert self.strategies[strategy].activation != 0, "inactive strategy"

            # Get the maximum amount the vault would withdraw from the strategy.
            to_withdraw: uint256 = min(
                # What we still need for the full withdraw.
                max_assets - have, 
                # The current debt the strategy has.
                self.strategies[strategy].current_debt
            )

            # Get any unrealised loss for the strategy.
            unrealised_loss: uint256 = self._assess_share_of_unrealised_losses(strategy, to_withdraw)

            # See if any limit is enforced by the strategy.
            strategy_limit: uint256 = IStrategy(strategy).convertToAssets(
                IStrategy(strategy).maxRedeem(self)
            )

            # Adjust accordingly if there is a max withdraw limit.
            realizable_withdraw: uint256 = to_withdraw - unrealised_loss
            if strategy_limit < realizable_withdraw:
                if unrealised_loss != 0:
                    # lower unrealised loss proportional to the limit.
                    unrealised_loss = unrealised_loss * strategy_limit / realizable_withdraw

                # Still count the unrealised loss as withdrawable.
                to_withdraw = strategy_limit + unrealised_loss
                
            # If 0 move on to the next strategy.
            if to_withdraw == 0:
                continue

            # If there would be a loss with a non-maximum `max_loss` value.
            if unrealised_loss > 0 and max_loss < MAX_BPS:
                # Check if the loss is greater than the allowed range.
                if loss + unrealised_loss > (have + to_withdraw) * max_loss / MAX_BPS:
                    # If so use the amounts up till now.
                    break

            # Add to what we can pull.
            have += to_withdraw

            # If we have all we need break.
            if have >= max_assets:
                break

            # Add any unrealised loss to the total
            loss += unrealised_loss

        # Update the max after going through the queue.
        # In case we broke early or exhausted the queue.
        max_assets = have

    return max_assets

@internal
def _deposit(sender: address, recipient: address, assets: uint256) -> uint256:
    """
    Used for `deposit` calls to transfer the amount of `asset` to the vault, 
    issue the corresponding shares to the `recipient` and update all needed 
    vault accounting.
    """
    assert self.shutdown == False # dev: shutdown
    assert assets <= self._max_deposit(recipient), "exceed deposit limit"
 
    # Transfer the tokens to the vault first.
    self._erc20_safe_transfer_from(self.asset, msg.sender, self, assets)
    # Record the change in total assets.
    self.total_idle += assets
    
    # Issue the corresponding shares for assets.
    shares: uint256 = self._issue_shares_for_amount(assets, recipient)

    assert shares > 0, "cannot mint zero"

    log Deposit(sender, recipient, assets, shares)
    return shares

@internal
def _mint(sender: address, recipient: address, shares: uint256) -> uint256:
    """
    Used for `mint` calls to issue the corresponding shares to the `recipient`,
    transfer the amount of `asset` to the vault, and update all needed vault 
    accounting.
    """
    assert self.shutdown == False # dev: shutdown
    # Get corresponding amount of assets.
    assets: uint256 = self._convert_to_assets(shares, Rounding.ROUND_UP)

    assert assets > 0, "cannot deposit zero"
    assert assets <= self._max_deposit(recipient), "exceed deposit limit"

    # Transfer the tokens to the vault first.
    self._erc20_safe_transfer_from(self.asset, msg.sender, self, assets)
    # Record the change in total assets.
    self.total_idle += assets
    
    # Issue the corresponding shares for assets.
    self._issue_shares(shares, recipient)

    log Deposit(sender, recipient, assets, shares)
    return assets

@view
@internal
def _assess_share_of_unrealised_losses(strategy: address, assets_needed: uint256) -> uint256:
    """
    Returns the share of losses that a user would take if withdrawing from this strategy
    This accounts for losses that have been realized at the strategy level but not yet
    realized at the vault level.

    e.g. if the strategy has unrealised losses for 10% of its current debt and the user 
    wants to withdraw 1_000 tokens, the losses that they will take is 100 token
    """
    # Minimum of how much debt the debt should be worth.
    strategy_current_debt: uint256 = self.strategies[strategy].current_debt
    # The actual amount that the debt is currently worth.
    vault_shares: uint256 = IStrategy(strategy).balanceOf(self)
    strategy_assets: uint256 = IStrategy(strategy).convertToAssets(vault_shares)
    
    # If no losses, return 0
    if strategy_assets >= strategy_current_debt or strategy_current_debt == 0:
        return 0

    # Users will withdraw assets_needed divided by loss ratio (strategy_assets / strategy_current_debt - 1).
    # NOTE: If there are unrealised losses, the user will take his share.
    numerator: uint256 = assets_needed * strategy_assets
    users_share_of_loss: uint256 = assets_needed - numerator / strategy_current_debt
    # Always round up.
    if numerator % strategy_current_debt != 0:
        users_share_of_loss += 1

    return users_share_of_loss

@internal
def _withdraw_from_strategy(strategy: address, assets_to_withdraw: uint256):
    """
    This takes the amount denominated in asset and performs a {redeem}
    with the corresponding amount of shares.

    We use {redeem} to natively take on losses without additional non-4626 standard parameters.
    """
    # Need to get shares since we use redeem to be able to take on losses.
    shares_to_redeem: uint256 = min(
        # Use previewWithdraw since it should round up.
        IStrategy(strategy).previewWithdraw(assets_to_withdraw), 
        # And check against our actual balance.
        IStrategy(strategy).balanceOf(self)
    )
    # Redeem the shares.
    IStrategy(strategy).redeem(shares_to_redeem, self, self)

@internal
def _redeem(
    sender: address, 
    receiver: address, 
    owner: address,
    assets: uint256,
    shares: uint256, 
    max_loss: uint256,
    strategies: DynArray[address, MAX_QUEUE]
) -> uint256:
    """
    This will attempt to free up the full amount of assets equivalent to
    `shares` and transfer them to the `receiver`. If the vault does
    not have enough idle funds it will go through any strategies provided by
    either the withdrawer or the default_queue to free up enough funds to 
    service the request.

    The vault will attempt to account for any unrealized losses taken on from
    strategies since their respective last reports.

    Any losses realized during the withdraw from a strategy will be passed on
    to the user that is redeeming their vault shares unless it exceeds the given
    `max_loss`.
    """
    assert receiver != empty(address), "ZERO ADDRESS"
    assert shares > 0, "no shares to redeem"
    assert assets > 0, "no assets to withdraw"
    assert max_loss <= MAX_BPS, "max loss"
    
    # If there is a withdraw limit module, check the max.
    withdraw_limit_module: address = self.withdraw_limit_module
    if withdraw_limit_module != empty(address):
        assert assets <= IWithdrawLimitModule(withdraw_limit_module).available_withdraw_limit(owner, max_loss, strategies), "exceed withdraw limit"

    assert self.balance_of[owner] >= shares, "insufficient shares to redeem"
    
    if sender != owner:
        self._spend_allowance(owner, sender, shares)

    # The amount of the underlying token to withdraw.
    requested_assets: uint256 = assets

    # load to memory to save gas
    current_total_idle: uint256 = self.total_idle
    _asset: address = self.asset

    # If there are not enough assets in the Vault contract, we try to free
    # funds from strategies.
    if requested_assets > current_total_idle:

        # Cache the default queue.
        _strategies: DynArray[address, MAX_QUEUE] = self.default_queue

        # If a custom queue was passed, and we don't force the default queue.
        if len(strategies) != 0 and not self.use_default_queue:
            # Use the custom queue.
            _strategies = strategies

        # load to memory to save gas
        current_total_debt: uint256 = self.total_debt

        # Withdraw from strategies only what idle doesn't cover.
        # `assets_needed` is the total amount we need to fill the request.
        assets_needed: uint256 = unsafe_sub(requested_assets, current_total_idle)
        # `assets_to_withdraw` is the amount to request from the current strategy.
        assets_to_withdraw: uint256 = 0

        # To compare against real withdrawals from strategies
        previous_balance: uint256 = ERC20(_asset).balanceOf(self)

        for strategy in _strategies:
            # Make sure we have a valid strategy.
            assert self.strategies[strategy].activation != 0, "inactive strategy"

            # How much should the strategy have.
            current_debt: uint256 = self.strategies[strategy].current_debt

            # What is the max amount to withdraw from this strategy.
            assets_to_withdraw = min(assets_needed, current_debt)

            # Cache max_withdraw now for use if unrealized loss > 0
            # Use maxRedeem and convert it since we use redeem.
            max_withdraw: uint256 = IStrategy(strategy).convertToAssets(
                IStrategy(strategy).maxRedeem(self)
            )

            # CHECK FOR UNREALISED LOSSES
            # If unrealised losses > 0, then the user will take the proportional share 
            # and realize it (required to avoid users withdrawing from lossy strategies).
            # NOTE: strategies need to manage the fact that realising part of the loss can 
            # mean the realisation of 100% of the loss!! (i.e. if for withdrawing 10% of the
            # strategy it needs to unwind the whole position, generated losses might be bigger)
            unrealised_losses_share: uint256 = self._assess_share_of_unrealised_losses(strategy, assets_to_withdraw)
            if unrealised_losses_share > 0:
                # If max withdraw is limiting the amount to pull, we need to adjust the portion of 
                # the unrealized loss the user should take.
                if max_withdraw < assets_to_withdraw - unrealised_losses_share:
                    # How much would we want to withdraw
                    wanted: uint256 = assets_to_withdraw - unrealised_losses_share
                    # Get the proportion of unrealised comparing what we want vs. what we can get
                    unrealised_losses_share = unrealised_losses_share * max_withdraw / wanted
                    # Adjust assets_to_withdraw so all future calculations work correctly
                    assets_to_withdraw = max_withdraw + unrealised_losses_share
                
                # User now "needs" less assets to be unlocked (as he took some as losses)
                assets_to_withdraw -= unrealised_losses_share
                requested_assets -= unrealised_losses_share
                # NOTE: done here instead of waiting for regular update of these values 
                # because it's a rare case (so we can save minor amounts of gas)
                assets_needed -= unrealised_losses_share
                current_total_debt -= unrealised_losses_share

                # If max withdraw is 0 and unrealised loss is still > 0 then the strategy likely
                # realized a 100% loss and we will need to realize that loss before moving on.
                if max_withdraw == 0 and unrealised_losses_share > 0:
                    # Adjust the strategy debt accordingly.
                    new_debt: uint256 = current_debt - unrealised_losses_share
        
                    # Update strategies storage
                    self.strategies[strategy].current_debt = new_debt
                    # Log the debt update
                    log DebtUpdated(strategy, current_debt, new_debt)

            # Adjust based on the max withdraw of the strategy.
            assets_to_withdraw = min(assets_to_withdraw, max_withdraw)

            # Can't withdraw 0.
            if assets_to_withdraw == 0:
                continue
            
            # WITHDRAW FROM STRATEGY
            self._withdraw_from_strategy(strategy, assets_to_withdraw)
            post_balance: uint256 = ERC20(_asset).balanceOf(self)
            
            # Always check against the real amounts.
            withdrawn: uint256 = post_balance - previous_balance
            loss: uint256 = 0
            # Check if we redeemed too much.
            if withdrawn > assets_to_withdraw:
                # Make sure we don't underflow in debt updates.
                if withdrawn > current_debt:
                    # Can't withdraw more than our debt.
                    assets_to_withdraw = current_debt
                else:
                    # Add the extra to how much we withdrew.
                    assets_to_withdraw += (unsafe_sub(withdrawn, assets_to_withdraw))

            # If we have not received what we expected, we consider the difference a loss.
            elif withdrawn < assets_to_withdraw:
                loss = unsafe_sub(assets_to_withdraw, withdrawn)

            # NOTE: strategy's debt decreases by the full amount but the total idle increases 
            # by the actual amount only (as the difference is considered lost).
            current_total_idle += (assets_to_withdraw - loss)
            requested_assets -= loss
            current_total_debt -= assets_to_withdraw

            # Vault will reduce debt because the unrealised loss has been taken by user
            new_debt: uint256 = current_debt - (assets_to_withdraw + unrealised_losses_share)
        
            # Update strategies storage
            self.strategies[strategy].current_debt = new_debt
            # Log the debt update
            log DebtUpdated(strategy, current_debt, new_debt)

            # Break if we have enough total idle to serve initial request.
            if requested_assets <= current_total_idle:
                break

            # We update the previous_balance variable here to save gas in next iteration.
            previous_balance = post_balance

            # Reduce what we still need. Safe to use assets_to_withdraw 
            # here since it has been checked against requested_assets
            assets_needed -= assets_to_withdraw

        # If we exhaust the queue and still have insufficient total idle, revert.
        assert current_total_idle >= requested_assets, "insufficient assets in vault"
        # Commit memory to storage.
        self.total_debt = current_total_debt

    # Check if there is a loss and a non-default value was set.
    if assets > requested_assets and max_loss < MAX_BPS:
        # Assure the loss is within the allowed range.
        assert assets - requested_assets <= assets * max_loss / MAX_BPS, "too much loss"

    # First burn the corresponding shares from the redeemer.
    self._burn_shares(shares, owner)
    # Commit memory to storage.
    self.total_idle = current_total_idle - requested_assets
    # Transfer the requested amount to the receiver.
    self._erc20_safe_transfer(_asset, receiver, requested_assets)

    log Withdraw(sender, receiver, owner, requested_assets, shares)
    return requested_assets

## STRATEGY MANAGEMENT ##
@internal
def _add_strategy(new_strategy: address, add_to_queue: bool):
    assert new_strategy not in [self, empty(address)], "strategy cannot be zero address"
    assert IStrategy(new_strategy).asset() == self.asset, "invalid asset"
    assert self.strategies[new_strategy].activation == 0, "strategy already active"

    # Add the new strategy to the mapping.
    self.strategies[new_strategy] = StrategyParams({
        activation: block.timestamp,
        last_report: block.timestamp,
        current_debt: 0,
        max_debt: 0
    })

    # If we are adding to the queue and the default queue has space, add the strategy.
    if add_to_queue and len(self.default_queue) < MAX_QUEUE:
        self.default_queue.append(new_strategy)        
        
    log StrategyChanged(new_strategy, StrategyChangeType.ADDED)

@internal
def _revoke_strategy(strategy: address, force: bool=False):
    assert self.strategies[strategy].activation != 0, "strategy not active"

    # If force revoking a strategy, it will cause a loss.
    loss: uint256 = 0
    
    if self.strategies[strategy].current_debt != 0:
        assert force, "strategy has debt"
        # Vault realizes the full loss of outstanding debt.
        loss = self.strategies[strategy].current_debt
        # Adjust total vault debt.
        self.total_debt -= loss

        log StrategyReported(strategy, 0, loss, 0, 0, 0, 0)

    # Set strategy params all back to 0 (WARNING: it can be re-added).
    self.strategies[strategy] = StrategyParams({
      activation: 0,
      last_report: 0,
      current_debt: 0,
      max_debt: 0
    })

    # Remove strategy if it is in the default queue.
    new_queue: DynArray[address, MAX_QUEUE] = []
    for _strategy in self.default_queue:
        # Add all strategies to the new queue besides the one revoked.
        if _strategy != strategy:
            new_queue.append(_strategy)
        
    # Set the default queue to our updated queue.
    self.default_queue = new_queue

    log StrategyChanged(strategy, StrategyChangeType.REVOKED)

# DEBT MANAGEMENT #
@internal
def _update_debt(strategy: address, target_debt: uint256, max_loss: uint256) -> uint256:
    """
    The vault will re-balance the debt vs target debt. Target debt must be
    smaller or equal to strategy's max_debt. This function will compare the 
    current debt with the target debt and will take funds or deposit new 
    funds to the strategy. 

    The strategy can require a maximum amount of funds that it wants to receive
    to invest. The strategy can also reject freeing funds if they are locked.
    """
    # How much we want the strategy to have.
    new_debt: uint256 = target_debt
    # How much the strategy currently has.
    current_debt: uint256 = self.strategies[strategy].current_debt

    # If the vault is shutdown we can only pull funds.
    if self.shutdown:
        new_debt = 0

    assert new_debt != current_debt, "new debt equals current debt"

    if current_debt > new_debt:
        # Reduce debt.
        assets_to_withdraw: uint256 = unsafe_sub(current_debt, new_debt)

        # Ensure we always have minimum_total_idle when updating debt.
        minimum_total_idle: uint256 = self.minimum_total_idle
        total_idle: uint256 = self.total_idle
        
        # Respect minimum total idle in vault
        if total_idle + assets_to_withdraw < minimum_total_idle:
            assets_to_withdraw = unsafe_sub(minimum_total_idle, total_idle)
            # Cant withdraw more than the strategy has.
            if assets_to_withdraw > current_debt:
                assets_to_withdraw = current_debt

        # Check how much we are able to withdraw.
        # Use maxRedeem and convert since we use redeem.
        withdrawable: uint256 = IStrategy(strategy).convertToAssets(
            IStrategy(strategy).maxRedeem(self)
        )
        assert withdrawable != 0, "nothing to withdraw"

        # If insufficient withdrawable, withdraw what we can.
        if withdrawable < assets_to_withdraw:
            assets_to_withdraw = withdrawable

        # If there are unrealised losses we don't let the vault reduce its debt until there is a new report
        unrealised_losses_share: uint256 = self._assess_share_of_unrealised_losses(strategy, assets_to_withdraw)
        assert unrealised_losses_share == 0, "strategy has unrealised losses"
        
        # Cache for repeated use.
        _asset: address = self.asset

        # Always check the actual amount withdrawn.
        pre_balance: uint256 = ERC20(_asset).balanceOf(self)
        self._withdraw_from_strategy(strategy, assets_to_withdraw)
        post_balance: uint256 = ERC20(_asset).balanceOf(self)
        
        # making sure we are changing idle according to the real result no matter what. 
        # We pull funds with {redeem} so there can be losses or rounding differences.
        withdrawn: uint256 = min(post_balance - pre_balance, current_debt)

        # If we didn't get the amount we asked for and there is a max loss.
        if withdrawn < assets_to_withdraw and max_loss < MAX_BPS:
            # Make sure the loss is within the allowed range.
            assert assets_to_withdraw - withdrawn <= assets_to_withdraw * max_loss / MAX_BPS, "too much loss"

        # If we got too much make sure not to increase PPS.
        elif withdrawn > assets_to_withdraw:
            assets_to_withdraw = withdrawn

        # Update storage.
        self.total_idle += withdrawn # actual amount we got.
        # Amount we tried to withdraw in case of losses
        self.total_debt -= assets_to_withdraw 

        new_debt = current_debt - assets_to_withdraw
    else: 
        # We are increasing the strategies debt

        # Revert if target_debt cannot be achieved due to configured max_debt for given strategy
        assert new_debt <= self.strategies[strategy].max_debt, "target debt higher than max debt"

        # Vault is increasing debt with the strategy by sending more funds.
        max_deposit: uint256 = IStrategy(strategy).maxDeposit(self)
        assert max_deposit != 0, "nothing to deposit"

        # Deposit the difference between desired and current.
        assets_to_deposit: uint256 = new_debt - current_debt
        if assets_to_deposit > max_deposit:
            # Deposit as much as possible.
            assets_to_deposit = max_deposit
        
        # Ensure we always have minimum_total_idle when updating debt.
        minimum_total_idle: uint256 = self.minimum_total_idle
        total_idle: uint256 = self.total_idle

        assert total_idle > minimum_total_idle, "no funds to deposit"
        available_idle: uint256 = unsafe_sub(total_idle, minimum_total_idle)

        # If insufficient funds to deposit, transfer only what is free.
        if assets_to_deposit > available_idle:
            assets_to_deposit = available_idle

        # Can't Deposit 0.
        if assets_to_deposit > 0:
            # Cache for repeated use.
            _asset: address = self.asset

            # Approve the strategy to pull only what we are giving it.
            self._erc20_safe_approve(_asset, strategy, assets_to_deposit)

            # Always update based on actual amounts deposited.
            pre_balance: uint256 = ERC20(_asset).balanceOf(self)
            IStrategy(strategy).deposit(assets_to_deposit, self)
            post_balance: uint256 = ERC20(_asset).balanceOf(self)

            # Make sure our approval is always back to 0.
            self._erc20_safe_approve(_asset, strategy, 0)

            # Making sure we are changing according to the real result no 
            # matter what. This will spend more gas but makes it more robust.
            assets_to_deposit = pre_balance - post_balance

            # Update storage.
            self.total_idle -= assets_to_deposit
            self.total_debt += assets_to_deposit

        new_debt = current_debt + assets_to_deposit

    # Commit memory to storage.
    self.strategies[strategy].current_debt = new_debt

    log DebtUpdated(strategy, current_debt, new_debt)
    return new_debt

## ACCOUNTING MANAGEMENT ##
@internal
def _process_report(strategy: address) -> (uint256, uint256):
    """
    Processing a report means comparing the debt that the strategy has taken 
    with the current amount of funds it is reporting. If the strategy owes 
    less than it currently has, it means it has had a profit, else (assets < debt) 
    it has had a loss.

    Different strategies might choose different reporting strategies: pessimistic, 
    only realised P&L, ... The best way to report depends on the strategy.

    The profit will be distributed following a smooth curve over the vaults 
    profit_max_unlock_time seconds. Losses will be taken immediately, first from the 
    profit buffer (avoiding an impact in pps), then will reduce pps.

    Any applicable fees are charged and distributed during the report as well
    to the specified recipients.
    """
    # Make sure we have a valid strategy.
    assert self.strategies[strategy].activation != 0, "inactive strategy"

    # Vault assesses profits using 4626 compliant interface. 
    # NOTE: It is important that a strategies `convertToAssets` implementation
    # cannot be manipulated or else the vault could report incorrect gains/losses.
    strategy_shares: uint256 = IStrategy(strategy).balanceOf(self)
    # How much the vaults position is worth.
    total_assets: uint256 = IStrategy(strategy).convertToAssets(strategy_shares)
    # How much the vault had deposited to the strategy.
    current_debt: uint256 = self.strategies[strategy].current_debt

    gain: uint256 = 0
    loss: uint256 = 0

    ### Asses Gain or Loss ###

    # Compare reported assets vs. the current debt.
    if total_assets > current_debt:
        # We have a gain.
        gain = unsafe_sub(total_assets, current_debt)
    else:
        # We have a loss.
        loss = unsafe_sub(current_debt, total_assets)
    
    # Cache `asset` for repeated use.
    _asset: address = self.asset

    ### Asses Fees and Refunds ###

    # For Accountant fee assessment.
    total_fees: uint256 = 0
    total_refunds: uint256 = 0
    # If accountant is not set, fees and refunds remain unchanged.
    accountant: address = self.accountant
    if accountant != empty(address):
        total_fees, total_refunds = IAccountant(accountant).report(strategy, gain, loss)

        if total_refunds > 0:
            # Make sure we have enough approval and enough asset to pull.
            total_refunds = min(total_refunds, min(ERC20(_asset).balanceOf(accountant), ERC20(_asset).allowance(accountant, self)))

    # Total fees to charge in shares.
    total_fees_shares: uint256 = 0
    # For Protocol fee assessment.
    protocol_fee_bps: uint16 = 0
    protocol_fees_shares: uint256 = 0
    protocol_fee_recipient: address = empty(address)
    # `shares_to_burn` is derived from amounts that would reduce the vaults PPS.
    # NOTE: this needs to be done before any pps changes
    shares_to_burn: uint256 = 0
    # Only need to burn shares if there is a loss or fees.
    if loss + total_fees > 0:
        # The amount of shares we will want to burn to offset losses and fees.
        shares_to_burn = self._convert_to_shares(loss + total_fees, Rounding.ROUND_UP)

        # If we have fees then get the proportional amount of shares to issue.
        if total_fees > 0:
            # Get the total amount shares to issue for the fees.
            total_fees_shares = shares_to_burn * total_fees / (loss + total_fees)

            # Get the protocol fee config for this vault.
            protocol_fee_bps, protocol_fee_recipient = IFactory(self.factory).protocol_fee_config()

            # If there is a protocol fee.
            if protocol_fee_bps > 0:
                # Get the percent of fees to go to protocol fees.
                protocol_fees_shares = total_fees_shares * convert(protocol_fee_bps, uint256) / MAX_BPS


    # Shares to lock is any amount that would otherwise increase the vaults PPS.
    shares_to_lock: uint256 = 0
    profit_max_unlock_time: uint256 = self.profit_max_unlock_time
    # Get the amount we will lock to avoid a PPS increase.
    if gain + total_refunds > 0 and profit_max_unlock_time != 0:
        shares_to_lock = self._convert_to_shares(gain + total_refunds, Rounding.ROUND_DOWN)

    # The total current supply including locked shares.
    total_supply: uint256 = self.total_supply
    # The total shares the vault currently owns. Both locked and unlocked.
    total_locked_shares: uint256 = self.balance_of[self]
    # Get the desired end amount of shares after all accounting.
    ending_supply: uint256 = total_supply + shares_to_lock - shares_to_burn - self._unlocked_shares()
    
    # If we will end with more shares than we have now.
    if ending_supply > total_supply:
        # Issue the difference.
        self._issue_shares(unsafe_sub(ending_supply, total_supply), self)

    # Else we need to burn shares.
    elif total_supply > ending_supply:
        # Can't burn more than the vault owns.
        to_burn: uint256 = min(unsafe_sub(total_supply, ending_supply), total_locked_shares)
        self._burn_shares(to_burn, self)

    # Adjust the amount to lock for this period.
    if shares_to_lock > shares_to_burn:
        # Don't lock fees or losses.
        shares_to_lock = unsafe_sub(shares_to_lock, shares_to_burn)
    else:
        shares_to_lock = 0

    # Pull refunds
    if total_refunds > 0:
        # Transfer the refunded amount of asset to the vault.
        self._erc20_safe_transfer_from(_asset, accountant, self, total_refunds)
        # Update storage to increase total assets.
        self.total_idle += total_refunds

    # Record any reported gains.
    if gain > 0:
        # NOTE: this will increase total_assets
        current_debt = unsafe_add(current_debt, gain)
        self.strategies[strategy].current_debt = current_debt
        self.total_debt += gain

    # Or record any reported loss
    elif loss > 0:
        current_debt = unsafe_sub(current_debt, loss)
        self.strategies[strategy].current_debt = current_debt
        self.total_debt -= loss

    # Issue shares for fees that were calculated above if applicable.
    if total_fees_shares > 0:
        # Accountant fees are (total_fees - protocol_fees).
        self._issue_shares(total_fees_shares - protocol_fees_shares, accountant)

        # If we also have protocol fees.
        if protocol_fees_shares > 0:
            self._issue_shares(protocol_fees_shares, protocol_fee_recipient)

    # Update unlocking rate and time to fully unlocked.
    total_locked_shares = self.balance_of[self]
    if total_locked_shares > 0:
        previously_locked_time: uint256 = 0
        _full_profit_unlock_date: uint256 = self.full_profit_unlock_date
        # Check if we need to account for shares still unlocking.
        if _full_profit_unlock_date > block.timestamp: 
            # There will only be previously locked shares if time remains.
            # We calculate this here since it will not occur every time we lock shares.
            previously_locked_time = (total_locked_shares - shares_to_lock) * (_full_profit_unlock_date - block.timestamp)

        # new_profit_locking_period is a weighted average between the remaining time of the previously locked shares and the profit_max_unlock_time
        new_profit_locking_period: uint256 = (previously_locked_time + shares_to_lock * profit_max_unlock_time) / total_locked_shares
        # Calculate how many shares unlock per second.
        self.profit_unlocking_rate = total_locked_shares * MAX_BPS_EXTENDED / new_profit_locking_period
        # Calculate how long until the full amount of shares is unlocked.
        self.full_profit_unlock_date = block.timestamp + new_profit_locking_period
        # Update the last profitable report timestamp.
        self.last_profit_update = block.timestamp
    else:
        # NOTE: only setting this to the 0 will turn in the desired effect, 
        # no need to update profit_unlocking_rate
        self.full_profit_unlock_date = 0
    
    # Record the report of profit timestamp.
    self.strategies[strategy].last_report = block.timestamp

    # We have to recalculate the fees paid for cases with an overall loss or no profit locking
    if loss + total_fees > gain + total_refunds or profit_max_unlock_time == 0:
        total_fees = self._convert_to_assets(total_fees_shares, Rounding.ROUND_DOWN)

    log StrategyReported(
        strategy,
        gain,
        loss,
        current_debt,
        total_fees * convert(protocol_fee_bps, uint256) / MAX_BPS, # Protocol Fees
        total_fees,
        total_refunds
    )

    return (gain, loss)

# SETTERS #
@external
def set_accountant(new_accountant: address):
    """
    @notice Set the new accountant address.
    @param new_accountant The new accountant address.
    """
    self._enforce_role(msg.sender, Roles.ACCOUNTANT_MANAGER)
    self.accountant = new_accountant

    log UpdateAccountant(new_accountant)

@external
def set_default_queue(new_default_queue: DynArray[address, MAX_QUEUE]):
    """
    @notice Set the new default queue array.
    @dev Will check each strategy to make sure it is active. But will not
        check that the same strategy is not added twice. maxRedeem and maxWithdraw
        return values may be inaccurate if a strategy is added twice.
    @param new_default_queue The new default queue array.
    """
    self._enforce_role(msg.sender, Roles.QUEUE_MANAGER)

    # Make sure every strategy in the new queue is active.
    for strategy in new_default_queue:
        assert self.strategies[strategy].activation != 0, "!inactive"

    # Save the new queue.
    self.default_queue = new_default_queue

    log UpdateDefaultQueue(new_default_queue)

@external
def set_use_default_queue(use_default_queue: bool):
    """
    @notice Set a new value for `use_default_queue`.
    @dev If set `True` the default queue will always be
        used no matter whats passed in.
    @param use_default_queue new value.
    """
    self._enforce_role(msg.sender, Roles.QUEUE_MANAGER)
    self.use_default_queue = use_default_queue

    log UpdateUseDefaultQueue(use_default_queue)

@external
def set_deposit_limit(deposit_limit: uint256, override: bool = False):
    """
    @notice Set the new deposit limit.
    @dev Can not be changed if a deposit_limit_module
    is set unless the override flag is true or if shutdown.
    @param deposit_limit The new deposit limit.
    @param override If a `deposit_limit_module` already set should be overridden.
    """
    assert self.shutdown == False # Dev: shutdown
    self._enforce_role(msg.sender, Roles.DEPOSIT_LIMIT_MANAGER)

    # If we are overriding the deposit limit module.
    if override:
        # Make sure it is set to address 0 if not already.
        if self.deposit_limit_module != empty(address):

            self.deposit_limit_module = empty(address)
            log UpdateDepositLimitModule(empty(address))
    else:  
        # Make sure the deposit_limit_module has been set to address(0).
        assert self.deposit_limit_module == empty(address), "using module"

    self.deposit_limit = deposit_limit

    log UpdateDepositLimit(deposit_limit)

@external
def set_deposit_limit_module(deposit_limit_module: address, override: bool = False):
    """
    @notice Set a contract to handle the deposit limit.
    @dev The default `deposit_limit` will need to be set to
    max uint256 since the module will override it or the override flag
    must be set to true to set it to max in 1 tx..
    @param deposit_limit_module Address of the module.
    @param override If a `deposit_limit` already set should be overridden.
    """
    assert self.shutdown == False # Dev: shutdown
    self._enforce_role(msg.sender, Roles.DEPOSIT_LIMIT_MANAGER)

    # If we are overriding the deposit limit
    if override:
        # Make sure it is max uint256 if not already.
        if self.deposit_limit != max_value(uint256):

            self.deposit_limit = max_value(uint256)
            log UpdateDepositLimit(max_value(uint256))
    else:
        # Make sure the deposit_limit has been set to uint max.
        assert self.deposit_limit == max_value(uint256), "using deposit limit"

    self.deposit_limit_module = deposit_limit_module

    log UpdateDepositLimitModule(deposit_limit_module)

@external
def set_withdraw_limit_module(withdraw_limit_module: address):
    """
    @notice Set a contract to handle the withdraw limit.
    @dev This will override the default `max_withdraw`.
    @param withdraw_limit_module Address of the module.
    """
    self._enforce_role(msg.sender, Roles.WITHDRAW_LIMIT_MANAGER)

    self.withdraw_limit_module = withdraw_limit_module

    log UpdateWithdrawLimitModule(withdraw_limit_module)

@external
def set_minimum_total_idle(minimum_total_idle: uint256):
    """
    @notice Set the new minimum total idle.
    @param minimum_total_idle The new minimum total idle.
    """
    self._enforce_role(msg.sender, Roles.MINIMUM_IDLE_MANAGER)
    self.minimum_total_idle = minimum_total_idle

    log UpdateMinimumTotalIdle(minimum_total_idle)

@external
def setProfitMaxUnlockTime(new_profit_max_unlock_time: uint256):
    """
    @notice Set the new profit max unlock time.
    @dev The time is denominated in seconds and must be less than 1 year.
        We only need to update locking period if setting to 0,
        since the current period will use the old rate and on the next
        report it will be reset with the new unlocking time.
    
        Setting to 0 will cause any currently locked profit to instantly
        unlock and an immediate increase in the vaults Price Per Share.

    @param new_profit_max_unlock_time The new profit max unlock time.
    """
    self._enforce_role(msg.sender, Roles.PROFIT_UNLOCK_MANAGER)
    # Must be less than one year for report cycles
    assert new_profit_max_unlock_time <= 31_556_952, "profit unlock time too long"

    # If setting to 0 we need to reset any locked values.
    if (new_profit_max_unlock_time == 0):

        share_balance: uint256 = self.balance_of[self]
        if share_balance > 0:
            # Burn any shares the vault still has.
            self._burn_shares(share_balance, self)

        # Reset unlocking variables to 0.
        self.profit_unlocking_rate = 0
        self.full_profit_unlock_date = 0

    self.profit_max_unlock_time = new_profit_max_unlock_time

    log UpdateProfitMaxUnlockTime(new_profit_max_unlock_time)

# ROLE MANAGEMENT #
@internal
def _enforce_role(account: address, role: Roles):
    # Make sure the sender holds the role.
    assert role in self.roles[account], "not allowed"

@external
def set_role(account: address, role: Roles):
    """
    @notice Set the roles for an account.
    @dev This will fully override an accounts current roles
     so it should include all roles the account should hold.
    @param account The account to set the role for.
    @param role The roles the account should hold.
    """
    assert msg.sender == self.role_manager
    self.roles[account] = role

    log RoleSet(account, role)

@external
def add_role(account: address, role: Roles):
    """
    @notice Add a new role to an address.
    @dev This will add a new role to the account
     without effecting any of the previously held roles.
    @param account The account to add a role to.
    @param role The new role to add to account.
    """
    assert msg.sender == self.role_manager
    self.roles[account] = self.roles[account] | role

    log RoleSet(account, self.roles[account])

@external
def remove_role(account: address, role: Roles):
    """
    @notice Remove a single role from an account.
    @dev This will leave all other roles for the 
     account unchanged.
    @param account The account to remove a Role from.
    @param role The Role to remove.
    """
    assert msg.sender == self.role_manager
    self.roles[account] = self.roles[account] & ~role

    log RoleSet(account, self.roles[account])
    
@external
def transfer_role_manager(role_manager: address):
    """
    @notice Step 1 of 2 in order to transfer the 
        role manager to a new address. This will set
        the future_role_manager. Which will then need
        to be accepted by the new manager.
    @param role_manager The new role manager address.
    """
    assert msg.sender == self.role_manager
    self.future_role_manager = role_manager

@external
def accept_role_manager():
    """
    @notice Accept the role manager transfer.
    """
    assert msg.sender == self.future_role_manager
    self.role_manager = msg.sender
    self.future_role_manager = empty(address)

    log UpdateRoleManager(msg.sender)

# VAULT STATUS VIEWS

@view
@external
def isShutdown() -> bool:
    """
    @notice Get if the vault is shutdown.
    @return Bool representing the shutdown status
    """
    return self.shutdown
@view
@external
def unlockedShares() -> uint256:
    """
    @notice Get the amount of shares that have been unlocked.
    @return The amount of shares that are have been unlocked.
    """
    return self._unlocked_shares()

@view
@external
def pricePerShare() -> uint256:
    """
    @notice Get the price per share (pps) of the vault.
    @dev This value offers limited precision. Integrations that require 
        exact precision should use convertToAssets or convertToShares instead.
    @return The price per share.
    """
    return self._convert_to_assets(10 ** convert(self.decimals, uint256), Rounding.ROUND_DOWN)

@view
@external
def get_default_queue() -> DynArray[address, MAX_QUEUE]:
    """
    @notice Get the full default queue currently set.
    @return The current default withdrawal queue.
    """
    return self.default_queue

## REPORTING MANAGEMENT ##
@external
@nonreentrant("lock")
def process_report(strategy: address) -> (uint256, uint256):
    """
    @notice Process the report of a strategy.
    @param strategy The strategy to process the report for.
    @return The gain and loss of the strategy.
    """
    self._enforce_role(msg.sender, Roles.REPORTING_MANAGER)
    return self._process_report(strategy)

@external
@nonreentrant("lock")
def buy_debt(strategy: address, amount: uint256):
    """
    @notice Used for governance to buy bad debt from the vault.
    @dev This should only ever be used in an emergency in place
    of force revoking a strategy in order to not report a loss.
    It allows the DEBT_PURCHASER role to buy the strategies debt
    for an equal amount of `asset`. 

    @param strategy The strategy to buy the debt for
    @param amount The amount of debt to buy from the vault.
    """
    self._enforce_role(msg.sender, Roles.DEBT_PURCHASER)
    assert self.strategies[strategy].activation != 0, "not active"
    
    # Cache the current debt.
    current_debt: uint256 = self.strategies[strategy].current_debt
    _amount: uint256 = amount

    assert current_debt > 0, "nothing to buy"
    assert _amount > 0, "nothing to buy with"
    
    if _amount > current_debt:
        _amount = current_debt

    # We get the proportion of the debt that is being bought and
    # transfer the equivalent shares. We assume this is being used
    # due to strategy issues so won't rely on its conversion rates.
    shares: uint256 = IStrategy(strategy).balanceOf(self) * _amount / current_debt

    assert shares > 0, "cannot buy zero"

    self._erc20_safe_transfer_from(self.asset, msg.sender, self, _amount)

    # Lower strategy debt
    self.strategies[strategy].current_debt -= _amount
    # lower total debt
    self.total_debt -= _amount
    # Increase total idle
    self.total_idle += _amount

    # log debt change
    log DebtUpdated(strategy, current_debt, current_debt - _amount)

    # Transfer the strategies shares out.
    self._erc20_safe_transfer(strategy, msg.sender, shares)

    log DebtPurchased(strategy, _amount)

## STRATEGY MANAGEMENT ##
@external
def add_strategy(new_strategy: address, add_to_queue: bool=True):
    """
    @notice Add a new strategy.
    @param new_strategy The new strategy to add.
    """
    self._enforce_role(msg.sender, Roles.ADD_STRATEGY_MANAGER)
    self._add_strategy(new_strategy, add_to_queue)

@external
def revoke_strategy(strategy: address):
    """
    @notice Revoke a strategy.
    @param strategy The strategy to revoke.
    """
    self._enforce_role(msg.sender, Roles.REVOKE_STRATEGY_MANAGER)
    self._revoke_strategy(strategy)

@external
def force_revoke_strategy(strategy: address):
    """
    @notice Force revoke a strategy.
    @dev The vault will remove the strategy and write off any debt left 
        in it as a loss. This function is a dangerous function as it can force a 
        strategy to take a loss. All possible assets should be removed from the 
        strategy first via update_debt. If a strategy is removed erroneously it 
        can be re-added and the loss will be credited as profit. Fees will apply.
    @param strategy The strategy to force revoke.
    """
    self._enforce_role(msg.sender, Roles.FORCE_REVOKE_MANAGER)
    self._revoke_strategy(strategy, True)

## DEBT MANAGEMENT ##
@external
def update_max_debt_for_strategy(strategy: address, new_max_debt: uint256):
    """
    @notice Update the max debt for a strategy.
    @param strategy The strategy to update the max debt for.
    @param new_max_debt The new max debt for the strategy.
    """
    self._enforce_role(msg.sender, Roles.MAX_DEBT_MANAGER)
    assert self.strategies[strategy].activation != 0, "inactive strategy"
    self.strategies[strategy].max_debt = new_max_debt

    log UpdatedMaxDebtForStrategy(msg.sender, strategy, new_max_debt)

@external
@nonreentrant("lock")
def update_debt(
    strategy: address, 
    target_debt: uint256, 
    max_loss: uint256 = MAX_BPS
) -> uint256:
    """
    @notice Update the debt for a strategy.
    @param strategy The strategy to update the debt for.
    @param target_debt The target debt for the strategy.
    @param max_loss Optional to check realized losses on debt decreases.
    @return The amount of debt added or removed.
    """
    self._enforce_role(msg.sender, Roles.DEBT_MANAGER)
    return self._update_debt(strategy, target_debt, max_loss)

## EMERGENCY MANAGEMENT ##
@external
def shutdown_vault():
    """
    @notice Shutdown the vault.
    """
    self._enforce_role(msg.sender, Roles.EMERGENCY_MANAGER)
    assert self.shutdown == False
    
    # Shutdown the vault.
    self.shutdown = True

    # Set deposit limit to 0.
    if self.deposit_limit_module != empty(address):
        self.deposit_limit_module = empty(address)

        log UpdateDepositLimitModule(empty(address))

    self.deposit_limit = 0
    log UpdateDepositLimit(0)

    self.roles[msg.sender] = self.roles[msg.sender] | Roles.DEBT_MANAGER
    log Shutdown()


## SHARE MANAGEMENT ##
## ERC20 + ERC4626 ##
@external
@nonreentrant("lock")
def deposit(assets: uint256, receiver: address) -> uint256:
    """
    @notice Deposit assets into the vault.
    @param assets The amount of assets to deposit.
    @param receiver The address to receive the shares.
    @return The amount of shares minted.
    """
    return self._deposit(msg.sender, receiver, assets)

@external
@nonreentrant("lock")
def mint(shares: uint256, receiver: address) -> uint256:
    """
    @notice Mint shares for the receiver.
    @param shares The amount of shares to mint.
    @param receiver The address to receive the shares.
    @return The amount of assets deposited.
    """
    return self._mint(msg.sender, receiver, shares)

@external
@nonreentrant("lock")
def withdraw(
    assets: uint256, 
    receiver: address, 
    owner: address, 
    max_loss: uint256 = 0,
    strategies: DynArray[address, MAX_QUEUE] = []
) -> uint256:
    """
    @notice Withdraw an amount of asset to `receiver` burning `owner`s shares.
    @dev The default behavior is to not allow any loss.
    @param assets The amount of asset to withdraw.
    @param receiver The address to receive the assets.
    @param owner The address who's shares are being burnt.
    @param max_loss Optional amount of acceptable loss in Basis Points.
    @param strategies Optional array of strategies to withdraw from.
    @return The amount of shares actually burnt.
    """
    shares: uint256 = self._convert_to_shares(assets, Rounding.ROUND_UP)
    self._redeem(msg.sender, receiver, owner, assets, shares, max_loss, strategies)
    return shares

@external
@nonreentrant("lock")
def redeem(
    shares: uint256, 
    receiver: address, 
    owner: address, 
    max_loss: uint256 = MAX_BPS,
    strategies: DynArray[address, MAX_QUEUE] = []
) -> uint256:
    """
    @notice Redeems an amount of shares of `owners` shares sending funds to `receiver`.
    @dev The default behavior is to allow losses to be realized.
    @param shares The amount of shares to burn.
    @param receiver The address to receive the assets.
    @param owner The address who's shares are being burnt.
    @param max_loss Optional amount of acceptable loss in Basis Points.
    @param strategies Optional array of strategies to withdraw from.
    @return The amount of assets actually withdrawn.
    """
    assets: uint256 = self._convert_to_assets(shares, Rounding.ROUND_DOWN)
    # Always return the actual amount of assets withdrawn.
    return self._redeem(msg.sender, receiver, owner, assets, shares, max_loss, strategies)


@external
def approve(spender: address, amount: uint256) -> bool:
    """
    @notice Approve an address to spend the vault's shares.
    @param spender The address to approve.
    @param amount The amount of shares to approve.
    @return True if the approval was successful.
    """
    return self._approve(msg.sender, spender, amount)

@external
def transfer(receiver: address, amount: uint256) -> bool:
    """
    @notice Transfer shares to a receiver.
    @param receiver The address to transfer shares to.
    @param amount The amount of shares to transfer.
    @return True if the transfer was successful.
    """
    assert receiver not in [self, empty(address)]
    self._transfer(msg.sender, receiver, amount)
    return True

@external
def transferFrom(sender: address, receiver: address, amount: uint256) -> bool:
    """
    @notice Transfer shares from a sender to a receiver.
    @param sender The address to transfer shares from.
    @param receiver The address to transfer shares to.
    @param amount The amount of shares to transfer.
    @return True if the transfer was successful.
    """
    assert receiver not in [self, empty(address)]
    return self._transfer_from(sender, receiver, amount)

## ERC20+4626 compatibility
@external
def permit(
    owner: address, 
    spender: address, 
    amount: uint256, 
    deadline: uint256, 
    v: uint8, 
    r: bytes32, 
    s: bytes32
) -> bool:
    """
    @notice Approve an address to spend the vault's shares.
    @param owner The address to approve.
    @param spender The address to approve.
    @param amount The amount of shares to approve.
    @param deadline The deadline for the permit.
    @param v The v component of the signature.
    @param r The r component of the signature.
    @param s The s component of the signature.
    @return True if the approval was successful.
    """
    return self._permit(owner, spender, amount, deadline, v, r, s)

@view
@external
def balanceOf(addr: address) -> uint256:
    """
    @notice Get the balance of a user.
    @param addr The address to get the balance of.
    @return The balance of the user.
    """
    if(addr == self):
        # If the address is the vault, account for locked shares.
        return self.balance_of[addr] - self._unlocked_shares()

    return self.balance_of[addr]

@view
@external
def totalSupply() -> uint256:
    """
    @notice Get the total supply of shares.
    @return The total supply of shares.
    """
    return self._total_supply()

@view
@external
def totalAssets() -> uint256:
    """
    @notice Get the total assets held by the vault.
    @return The total assets held by the vault.
    """
    return self._total_assets()

@view
@external
def totalIdle() -> uint256:
    """
    @notice Get the amount of loose `asset` the vault holds.
    @return The current total idle.
    """
    return self.total_idle

@view
@external
def totalDebt() -> uint256:
    """
    @notice Get the the total amount of funds invested
    across all strategies.
    @return The current total debt.
    """
    return self.total_debt

@view
@external
def convertToShares(assets: uint256) -> uint256:
    """
    @notice Convert an amount of assets to shares.
    @param assets The amount of assets to convert.
    @return The amount of shares.
    """
    return self._convert_to_shares(assets, Rounding.ROUND_DOWN)

@view
@external
def previewDeposit(assets: uint256) -> uint256:
    """
    @notice Preview the amount of shares that would be minted for a deposit.
    @param assets The amount of assets to deposit.
    @return The amount of shares that would be minted.
    """
    return self._convert_to_shares(assets, Rounding.ROUND_DOWN)

@view
@external
def previewMint(shares: uint256) -> uint256:
    """
    @notice Preview the amount of assets that would be deposited for a mint.
    @param shares The amount of shares to mint.
    @return The amount of assets that would be deposited.
    """
    return self._convert_to_assets(shares, Rounding.ROUND_UP)

@view
@external
def convertToAssets(shares: uint256) -> uint256:
    """
    @notice Convert an amount of shares to assets.
    @param shares The amount of shares to convert.
    @return The amount of assets.
    """
    return self._convert_to_assets(shares, Rounding.ROUND_DOWN)

@view
@external
def maxDeposit(receiver: address) -> uint256:
    """
    @notice Get the maximum amount of assets that can be deposited.
    @param receiver The address that will receive the shares.
    @return The maximum amount of assets that can be deposited.
    """
    return self._max_deposit(receiver)

@view
@external
def maxMint(receiver: address) -> uint256:
    """
    @notice Get the maximum amount of shares that can be minted.
    @param receiver The address that will receive the shares.
    @return The maximum amount of shares that can be minted.
    """
    max_deposit: uint256 = self._max_deposit(receiver)
    return self._convert_to_shares(max_deposit, Rounding.ROUND_DOWN)

@view
@external
def maxWithdraw(
    owner: address,
    max_loss: uint256 = 0,
    strategies: DynArray[address, MAX_QUEUE] = []
) -> uint256:
    """
    @notice Get the maximum amount of assets that can be withdrawn.
    @dev Complies to normal 4626 interface and takes custom params.
    NOTE: Passing in a incorrectly ordered queue may result in
     incorrect returns values.
    @param owner The address that owns the shares.
    @param max_loss Custom max_loss if any.
    @param strategies Custom strategies queue if any.
    @return The maximum amount of assets that can be withdrawn.
    """
    return self._max_withdraw(owner, max_loss, strategies)

@view
@external
def maxRedeem(
    owner: address,
    max_loss: uint256 = MAX_BPS,
    strategies: DynArray[address, MAX_QUEUE] = []
) -> uint256:
    """
    @notice Get the maximum amount of shares that can be redeemed.
    @dev Complies to normal 4626 interface and takes custom params.
    NOTE: Passing in a incorrectly ordered queue may result in
     incorrect returns values.
    @param owner The address that owns the shares.
    @param max_loss Custom max_loss if any.
    @param strategies Custom strategies queue if any.
    @return The maximum amount of shares that can be redeemed.
    """
    return min(
        # Min of the shares equivalent of max_withdraw or the full balance
        self._convert_to_shares(self._max_withdraw(owner, max_loss, strategies), Rounding.ROUND_DOWN),
        self.balance_of[owner]
    )

@view
@external
def previewWithdraw(assets: uint256) -> uint256:
    """
    @notice Preview the amount of shares that would be redeemed for a withdraw.
    @param assets The amount of assets to withdraw.
    @return The amount of shares that would be redeemed.
    """
    return self._convert_to_shares(assets, Rounding.ROUND_UP)

@view
@external
def previewRedeem(shares: uint256) -> uint256:
    """
    @notice Preview the amount of assets that would be withdrawn for a redeem.
    @param shares The amount of shares to redeem.
    @return The amount of assets that would be withdrawn.
    """
    return self._convert_to_assets(shares, Rounding.ROUND_DOWN)

@view
@external
def FACTORY() -> address:
    """
    @notice Address of the factory that deployed the vault.
    @dev Is used to retrieve the protocol fees.
    @return Address of the vault factory.
    """
    return self.factory

@view
@external
def apiVersion() -> String[28]:
    """
    @notice Get the API version of the vault.
    @return The API version of the vault.
    """
    return API_VERSION

@view
@external
def assess_share_of_unrealised_losses(strategy: address, assets_needed: uint256) -> uint256:
    """
    @notice Assess the share of unrealised losses that a strategy has.
    @param strategy The address of the strategy.
    @param assets_needed The amount of assets needed to be withdrawn.
    @return The share of unrealised losses that the strategy has.
    """
    assert self.strategies[strategy].current_debt >= assets_needed

    return self._assess_share_of_unrealised_losses(strategy, assets_needed)

## Profit locking getter functions ##

@view
@external
def profitMaxUnlockTime() -> uint256:
    """
    @notice Gets the current time profits are set to unlock over.
    @return The current profit max unlock time.
    """
    return self.profit_max_unlock_time

@view
@external
def fullProfitUnlockDate() -> uint256:
    """
    @notice Gets the timestamp at which all profits will be unlocked.
    @return The full profit unlocking timestamp
    """
    return self.full_profit_unlock_date

@view
@external
def profitUnlockingRate() -> uint256:
    """
    @notice The per second rate at which profits are unlocking.
    @dev This is denominated in EXTENDED_BPS decimals.
    @return The current profit unlocking rate.
    """
    return self.profit_unlocking_rate


@view
@external
def lastProfitUpdate() -> uint256:
    """
    @notice The timestamp of the last time shares were locked.
    @return The last profit update.
    """
    return self.last_profit_update

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
    """
    @notice Get the domain separator.
    @return The domain separator.
    """
    return self.domain_separator()
