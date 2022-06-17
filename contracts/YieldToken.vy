# @version 0.3.3

from vyper.interfaces import ERC20
# from vyper.interfaces import ERC4626

implements: ERC20
# implements: ERC4626

interface IVault:
   def asset() -> address: view
   def balanceOf(account: address) -> uint256: view
   def deposit(assets: uint256, recipient: address, depositor: address) -> uint256: nonpayable
   def redeem(shares: uint256, recipient: address, strategies: DynArray[address, 10]) -> uint256: nonpayable
   def totalAssets() -> uint256: nonpayable
   def convertToShares(assets: uint256) -> uint256: nonpayable
   def convertToAssets(shares: uint256) -> uint256: nonpayable
   def maxDeposit(owner: address) -> uint256: nonpayable

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

## STORAGE ##
ASSET: immutable(address)
VAULT: immutable(address)

name: public(String[64])
symbol: public(String[32])
decimals: public(uint256)

balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])

# `nonces` track `permit` approvals with signature.
nonces: public(HashMap[address, uint256])
DOMAIN_SEPARATOR: public(bytes32)
DOMAIN_TYPE_HASH: constant(bytes32) = keccak256('EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)')
PERMIT_TYPE_HASH: constant(bytes32) = keccak256("Permit(address owner,address spender,uint256 value,uint256 nonce,uint256 deadline)")

@external
def __init__(vault: address):
    VAULT = vault
    ASSET = IVault(vault).asset()

## ERC20 ##
@external
def totalSupply() -> uint256:
   return IVault(VAULT).balanceOf(self)

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



## ERC4626 ## 
@external
def asset() -> address:
   return ASSET

@external
def totalAssets() -> uint256:
   return IVault(VAULT).totalAssets()

@external
def convertToShares(assets: uint256) -> uint256:
   return IVault(VAULT).convertToShares(assets)

@external
def convertToAssets(shares: uint256) -> uint256:
   return IVault(VAULT).convertToAssets(shares)

@external
def maxDeposit(owner: address) -> uint256:
   return IVault(VAULT).maxDeposit(self)

@external
def maxMint(owner: address) -> uint256: 
   maxDeposit: uint256 = IVault(VAULT).maxDeposit(self)
   return IVault(VAULT).convertToShares(maxDeposit)

@external
def maxWithdraw(owner: address) -> uint256:
   return IVault(VAULT).convertToAssets(self.balanceOf[owner])

@external
def maxRedeem(owner: address) -> uint256:
   return self.balanceOf[owner]

@external
def previewDeposit(assets: uint256) -> uint256:
   return IVault(VAULT).convertToShares(assets)

@external
def previewWithdraw(shares: uint256) -> uint256:
    return IVault(VAULT).convertToAssets(shares)

@internal
def _deposit(fnCaller: address, receiver: address, assets: uint256) -> uint256:
   shares: uint256 = IVault(VAULT).deposit(assets, self, fnCaller)

   # NOTE: totalSupply has been replaced by vault.balanceOf(self)
   self.balanceOf[receiver] += shares 

   log Deposit(fnCaller, receiver, assets, shares)
   return shares

@internal
def _redeem(fnCaller: address, receiver: address, owner: address, shares: uint256) -> uint256:
    if fnCaller != owner: 
      self._spendAllowance(owner, msg.sender, shares)
    
    # NOTE: totalSupply has been replaced by vault.balanceOf(self)
    self.balanceOf[owner] -= shares 

    # TODO: implement withdrawal queue?
    assets: uint256 = IVault(VAULT).redeem(shares, receiver, [])
    log Withdraw(msg.sender, receiver, owner, assets, shares)
    return assets

@external
def deposit(assets: uint256, receiver: address = msg.sender) -> uint256:
   return self._deposit(msg.sender, receiver, assets)

@external
def mint(shares: uint256, receiver: address) -> uint256:
   assets: uint256 = IVault(VAULT).convertToAssets(shares)
   self._deposit(msg.sender, receiver, assets)
   return assets

@external
def withdraw(assets: uint256, receiver: address = msg.sender, owner: address = msg.sender) -> uint256:
   shares: uint256 = IVault(VAULT).convertToShares(assets)
   self._redeem(msg.sender, receiver, owner, shares)
   return shares

# TODO: withdraw / redeem with custom strategies

@external
def redeem(shares: uint256, receiver: address = msg.sender, owner: address = msg.sender) -> uint256:
   assets: uint256 = self._redeem(msg.sender, receiver, owner, shares)
   return assets

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

@external
def yVaultDepositCallback(amount: uint256, depositor: address):
    if amount > 0: 
       self.erc20_safe_transferFrom(ASSET, depositor, msg.sender, amount)


