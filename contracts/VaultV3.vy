from vyper.interfaces import ERC20

implements: ERC20


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


# STORAGE #
depositLimit: public(uint256)
totalDebt: public(uint256)


# STRUCTS #


# USER FACING FUNCTIONS #
@external
def deposit():


@external
def withdraw():


# SHARE MANAGEMENT FUNCTIONS #

def pricePerShare():


def sharesForAmount():


def amountForShares():


# STRATEGY MANAGEMENT FUNCTIONS #
def addStrategy():


def revokeStrategy():


def migrateStrategy():


# P&L MANAGEMENT FUNCTIONS #
def processReport():


def forceProcessReport(): 


# DEBT MANAGEMENT FUNCTIONS #
def updateDebt():


def updateDebtEmergency():






