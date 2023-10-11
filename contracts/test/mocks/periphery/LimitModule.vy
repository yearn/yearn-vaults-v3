# @version 0.3.7

interface IVault:
    def totalAssets() -> uint256: view

enforce_whitelist: public(bool)

whitelist: public(HashMap[address, bool])

default_deposit_limit: public(uint256)

default_withdraw_limit: public(uint256)

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

    if self.default_deposit_limit == MAX_UINT256:
        return MAX_UINT256
        
    return self.default_deposit_limit - IVault(msg.sender).totalAssets()

@view
@external
def available_withdraw_limit(owner: address, max_loss: uint256, strategies: DynArray[address, 10]) -> uint256:
    return self.default_withdraw_limit

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
def set_enforce_whitelist(enforce: bool):
    self.enforce_whitelist = enforce