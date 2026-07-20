# @version 0.3.10
#pragma evm-version paris

interface IVault:
    def totalAssets() -> uint256: view
    def balanceOf(owner: address) -> uint256: view
    def allowance(owner: address, spender: address) -> uint256: view
    def transfer(receiver: address, amount: uint256) -> bool: nonpayable
    def transferFrom(sender: address, receiver: address, amount: uint256) -> bool: nonpayable
    def redeem(shares: uint256, receiver: address, owner: address) -> uint256: nonpayable

event TransferHookCalled:
    caller: indexed(address)
    sender: indexed(address)
    receiver: indexed(address)
    shares: uint256

enforce_whitelist: public(bool)

whitelist: public(HashMap[address, bool])

default_deposit_limit: public(uint256)

default_withdraw_limit: public(uint256)

required_withdraw_strategy: public(address)

last_deposit_sender: public(address)

last_deposit_receiver: public(address)

last_deposit_assets: public(uint256)

last_deposit_shares: public(uint256)

post_deposit_count: public(uint256)

last_withdraw_sender: public(address)

last_withdraw_receiver: public(address)

last_withdraw_owner: public(address)

last_withdraw_assets: public(uint256)

last_withdraw_shares: public(uint256)

post_withdraw_count: public(uint256)

last_transfer_caller: public(address)

last_transfer_sender: public(address)

last_transfer_receiver: public(address)

last_transfer_shares: public(uint256)

last_transfer_sender_balance: public(uint256)

last_transfer_receiver_balance: public(uint256)

last_transfer_allowance: public(uint256)

post_transfer_count: public(uint256)

revert_post_deposit: public(bool)

revert_post_withdraw: public(bool)

revert_post_transfer: public(bool)

# 0 = disabled, 1 = transfer, 2 = transferFrom, 3 = redeem.
post_transfer_reentry_mode: public(uint256)

reentry_sender: public(address)

reentry_receiver: public(address)

reentry_amount: public(uint256)

reenter_post_deposit: public(bool)

@external
def __init__(
    default_deposit_limit: uint256,
    default_withdraw_limit: uint256,
    enforce_whitelist: bool
):
    self.default_deposit_limit = default_deposit_limit
    self.default_withdraw_limit = default_withdraw_limit
    self.enforce_whitelist = enforce_whitelist

@view
@external
def available_deposit_limit(receiver: address) -> uint256:
    if self.enforce_whitelist:
        if not self.whitelist[receiver]:
            return 0

    if self.default_deposit_limit == max_value(uint256):
        return max_value(uint256)
        
    return self.default_deposit_limit - IVault(msg.sender).totalAssets()

@view
@external
def available_withdraw_limit(owner: address, max_loss: uint256, strategies: DynArray[address, 10]) -> uint256:
    if self.required_withdraw_strategy != empty(address):
        if len(strategies) == 0:
            return 0
        if strategies[0] != self.required_withdraw_strategy:
            return 0

    return self.default_withdraw_limit

@external
def post_deposit(sender: address, receiver: address, assets: uint256, shares: uint256):
    assert not self.revert_post_deposit, "post deposit revert"

    self.last_deposit_sender = sender
    self.last_deposit_receiver = receiver
    self.last_deposit_assets = assets
    self.last_deposit_shares = shares
    self.post_deposit_count += 1

    if self.reenter_post_deposit:
        success: bool = IVault(msg.sender).transfer(self.reentry_receiver, self.reentry_amount)
        assert success

@external
def post_withdraw(sender: address, receiver: address, owner: address, assets: uint256, shares: uint256):
    assert not self.revert_post_withdraw, "post withdraw revert"

    self.last_withdraw_sender = sender
    self.last_withdraw_receiver = receiver
    self.last_withdraw_owner = owner
    self.last_withdraw_assets = assets
    self.last_withdraw_shares = shares
    self.post_withdraw_count += 1

@external
def post_transfer(caller: address, sender: address, receiver: address, shares: uint256):
    assert not self.revert_post_transfer, "post transfer revert"

    self.last_transfer_caller = caller
    self.last_transfer_sender = sender
    self.last_transfer_receiver = receiver
    self.last_transfer_shares = shares
    self.last_transfer_sender_balance = IVault(msg.sender).balanceOf(sender)
    self.last_transfer_receiver_balance = IVault(msg.sender).balanceOf(receiver)
    self.last_transfer_allowance = IVault(msg.sender).allowance(sender, caller)
    self.post_transfer_count += 1

    log TransferHookCalled(caller, sender, receiver, shares)

    reentry_mode: uint256 = self.post_transfer_reentry_mode
    # Make every attempt one-shot. If the nested call succeeds without a lock, its own
    # transfer callback must not recurse until gas exhaustion and fake a lock failure.
    self.post_transfer_reentry_mode = 0
    if reentry_mode == 1:
        success: bool = IVault(msg.sender).transfer(self.reentry_receiver, self.reentry_amount)
        assert success
    elif reentry_mode == 2:
        success: bool = IVault(msg.sender).transferFrom(
            self.reentry_sender,
            self.reentry_receiver,
            self.reentry_amount,
        )
        assert success
    elif reentry_mode == 3:
        redeemed_assets: uint256 = IVault(msg.sender).redeem(1, self, self)
        assert redeemed_assets > 0

@external
def set_whitelist(list: address):
    self.whitelist[list] = True

@external
def set_default_deposit_limit(limit: uint256):
    self.default_deposit_limit = limit

@external
def set_default_withdraw_limit(limit: uint256):
    self.default_withdraw_limit = limit

@external
def set_required_withdraw_strategy(strategy: address):
    self.required_withdraw_strategy = strategy

@external
def set_enforce_whitelist(enforce: bool):
    self.enforce_whitelist = enforce

@external
def set_revert_post_deposit(should_revert: bool):
    self.revert_post_deposit = should_revert

@external
def set_revert_post_withdraw(should_revert: bool):
    self.revert_post_withdraw = should_revert

@external
def set_revert_post_transfer(should_revert: bool):
    self.revert_post_transfer = should_revert

@external
def set_post_transfer_reentry(mode: uint256, sender: address, receiver: address, amount: uint256):
    assert mode <= 3
    self.post_transfer_reentry_mode = mode
    self.reentry_sender = sender
    self.reentry_receiver = receiver
    self.reentry_amount = amount

@external
def set_reenter_post_deposit(should_reenter: bool, receiver: address, amount: uint256):
    self.reenter_post_deposit = should_reenter
    self.reentry_receiver = receiver
    self.reentry_amount = amount
