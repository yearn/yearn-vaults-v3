# @version 0.3.3

from vyper.interfaces import ERC20

# TODO: external contract: factory
# TODO: external contract: access control
# TODO: external contract: fee manager
# TODO: external contract: healtcheck

# INTERFACES #
interface Strategy:
   def asset() -> address: view

# EVENTS #
event Transfer: 
   sender: indexed(address)
   receiver: indexed(address)
   value: uint256

# STRUCTS #
# TODO: strategy params
struct StrategyParams: 
   activation: uint256

# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000

# STORAGE #
asset: public(ERC20)
totalIdle: public(uint256)
strategies: public(HashMap[address, StrategyParams])

@external
def __init__():
   # TODO: implement
   return

# SUPPORT FUNCTIONS #
@internal
def _issueSharesForAmount(amount: uint256, recipient: address) -> uint256:
    # TODO: implement
    return 0
 
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
   assert _recipient not in [self, ZERO_ADDRESS]
   amount: uint256 = _amount

   if amount == MAX_UINT256:
   	amount = self.asset.balanceOf(msg.sender)

   assert amount > 0
   # TODO: should it check deposit limit?

   shares: uint256 = self._issueSharesForAmount(amount, _recipient)
   
   self.erc20_safe_transferFrom(self.asset.address, msg.sender, self, amount)
   self.totalIdle += amount

   return shares

# @external
# def withdraw(shares: uint256, owner: address, strategies: DynArray[address, 10]):
#    # TODO: implement withdrawal
#    #    - checks that the msg.sender is approved by owner
#    #    - checks the owner has enough shares
#    #    - checks the vault has enough tokens
#    #    - if not enough tokens: withdraw from the strategies in from_strategies list
#    #    - burn shares
#    #    - transfer tokens
#     return
# 
#    
# 
# 
# 
# # SHARE MANAGEMENT FUNCTIONS #
# def pricePerShare():
#    # TODO: returns the value of 1 share in 1 token (amountForShares(1e(decimals)))
#     return
# 
# def sharesForAmount(amount: uint256):
#    # TODO: convert the input amount of tokens into shares
#     return
# 
# def amountForShares(shares: uint256):
#    # TODO: conver the input amount of shares into tokens
#     return
# 
# # STRATEGY MANAGEMENT FUNCTIONS #
# def addStrategy(new_strategy: address):
#    # permissioned: STRATEGY_MANAGER
#    # TODO: implement adding a strategy
#    #     - verify validity
#    #     - add the strategy to the hashmap
#    #     - 
#     return
# 
# def revokeStrategy(old_strategy: address):
#    # permissioned: STRATEGY_MANAGER
#    # TODO: implement removing a strategy from the list
#    #     - verify strategy exists
#    #     - handle current status (does it have debt? is it locked?) 
#    #     - remove strategy from the hashmap
#     return
# 
# def migrateStrategy(new_strategy: address, old_strategy: address)):
#    # permissioned: STRATEGY_MANAGER
#    # TODO: implement migration of a strategy. this means that the old strategy will be revoked and the new one will be added
#    # the new one will inherit all the parameters from the old one, excluding the activation date
#     return
# 
# # P&L MANAGEMENT FUNCTIONS #
# def processReport(strategy: address):
#    # permissioned: ACCOUNTING_MANAGER (open?)
#    # TODO: calculate the P&L of the strategy and save the new status
#    # the way is to compare the strategy's assets with the debt with the vault
#    # strategy_assets > strategy_debt? profit. else loss
#    #    - lock the profit !
#    #    - implement the healthcheck
#     return
# 
# def forceProcessReport(strategy: address): 
#    # permissioned: ACCOUNTING_MANAGER
#    # TODO: allows processing the report with losses ! this should only be called in special situations
#    #    - deactivate the healthcheck
#    #    - call process report
#     return
# 
# # DEBT MANAGEMENT FUNCTIONS #
# def setMaxDebtForStrategy(strategy: address, maxAmount: uint256):
#    # permissioned: DEBT_MANAGER
#    # TODO: change maxDebt in strategy params for _strategy
#     return
# 
# def updateDebt():
#    # permissioned: DEBT_MANAGER (or maybe open?)
#    # TODO: rebalance debt. if the strategy is allowed to take more debt and the strategy wants that debt, the vault will send more. if the strategy has too much debt, the vault will have less
#    #    - retrieve current position
#    #    - retrieve max debt allocated
#    #    - check the strategy wants that debt
#    #    - 
#     return
# 
# def updateDebtEmergency():
#    # permissioned: EMERGENCY_DEBT_MANAGER
#    # TODO: use a different function to rebalance the debt. this function allows to incur into losses while withdrawing
#    # this function needs to be called through private mempool as could have MEV
#     return
# 
# 
# # EMERGENCY FUNCTIONS #
# def setEmergencyShutdown(emergency: bool):
#    # permissioned: EMERGENCY_MANAGER
#    # TODO: change emergency shutdown flag
#     return
# 
# # SETTERS #
# def setHealthcheck(newhealtcheck: address):
#    # permissioned: SETTER
#    # TODO: change healtcheck contract
#     return
# 
# def setFeeManager(newFeeManager: address):
#    # TODO: change feemanager contract
#     return
# 
# 

