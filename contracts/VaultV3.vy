from vyper.interfaces import ERC20

implements: ERC20
# TODO: external contract: factory
# TODO: external contract: access control
# TODO: external contract: fee manager
# TODO: external contract: healtcheck

# INTERFACES #
interface DetailedERC20:
   def name() -> String[42]: view
   def symbol() -> String[20]: view
   def decimals() -> uint256: view

interface Strategy:
   def asset() -> address: view

# EVENTS #
event Transfer: 
   sender: indexed(address)
   receiver: indexed(address)
   value: uint256

# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000

# STORAGE #
strategies: public(HashMap[address, StrategyParams])

# STRUCTS #
# TODO: strategy params

def __init__():
   # TODO: implement

# USER FACING FUNCTIONS #
@external
def deposit(amount: uint256, recipient: address):
   # TODO: implement deposits
   #    - checks deposit limit
   #    - checks user has enough tokens
   #    - calculate amount of shares to mint
   #    - transfer tokens to vault
   #    - mint shares


@external
def withdraw(shares: uint256, owner: address, strategies: DynArray[address, 10]):
   # TODO: implement withdrawal
   #    - checks that the msg.sender is approved by owner
   #    - checks the owner has enough shares
   #    - checks the vault has enough tokens
   #    - if not enough tokens: withdraw from the strategies in from_strategies list
   #    - burn shares
   #    - transfer tokens


# SHARE MANAGEMENT FUNCTIONS #
def pricePerShare():
   # TODO: returns the value of 1 share in 1 token (amountForShares(1e(decimals)))

def sharesForAmount(amount: uint256):
   # TODO: convert the input amount of tokens into shares

def amountForShares(shares: uint256):
   # TODO: conver the input amount of shares into tokens

# STRATEGY MANAGEMENT FUNCTIONS #
def addStrategy(new_strategy: address):
   # permissioned: STRATEGY_MANAGER
   # TODO: implement adding a strategy
   #     - verify validity
   #     - add the strategy to the hashmap
   #     - 

def revokeStrategy(old_strategy: address):
   # permissioned: STRATEGY_MANAGER
   # TODO: implement removing a strategy from the list
   #     - verify strategy exists
   #     - handle current status (does it have debt? is it locked?) 
   #     - remove strategy from the hashmap

def migrateStrategy(new_strategy: address, old_strategy: address)):
   # permissioned: STRATEGY_MANAGER
   # TODO: implement migration of a strategy. this means that the old strategy will be revoked and the new one will be added
   # the new one will inherit all the parameters from the old one, excluding the activation date

# P&L MANAGEMENT FUNCTIONS #
def processReport(strategy: address):
   # permissioned: ACCOUNTING_MANAGER (open?)
   # TODO: calculate the P&L of the strategy and save the new status
   # the way is to compare the strategy's assets with the debt with the vault
   # strategy_assets > strategy_debt? profit. else loss
   #    - lock the profit !
   #    - implement the healthcheck

def forceProcessReport(strategy: address): 
   # permissioned: ACCOUNTING_MANAGER
   # TODO: allows processing the report with losses ! this should only be called in special situations
   #    - deactivate the healthcheck
   #    - call process report

# DEBT MANAGEMENT FUNCTIONS #
def setMaxDebtForStrategy(strategy: address, maxAmount: uint256):
   # permissioned: DEBT_MANAGER
   # TODO: change maxDebt in strategy params for _strategy

def updateDebt():
   # permissioned: DEBT_MANAGER (or maybe open?)
   # TODO: rebalance debt. if the strategy is allowed to take more debt and the strategy wants that debt, the vault will send more. if the strategy has too much debt, the vault will have less
   #    - retrieve current position
   #    - retrieve max debt allocated
   #    - check the strategy wants that debt
   #    - 

def updateDebtEmergency():
   # permissioned: EMERGENCY_DEBT_MANAGER
   # TODO: use a different function to rebalance the debt. this function allows to incur into losses while withdrawing
   # this function needs to be called through private mempool as could have MEV


# EMERGENCY FUNCTIONS #
def setEmergencyShutdown(emergency: bool):
   # permissioned: EMERGENCY_MANAGER
   # TODO: change emergency shutdown flag

# SETTERS #
def setHealthcheck(newhealtcheck: address):
   # permissioned: SETTER
   # TODO: change healtcheck contract

def setFeeManager(newFeeManager: address):
   # TODO: change feemanager contract

