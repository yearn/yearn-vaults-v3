# Yearn System Specification (DRAFT)

### Definitions
TODO: fill these definitions
- VAULT: 
- ASSET:
- SHARE: 
- DEPOSITOR: 
- STRATEGY: 
- ROLES:
    - role_manager
    - ACCOUNTING_MANAGER
    - DEBT_MANAGER
    - STRATEGY_MANAGER
    - EMERGENCY_MANAGER

# VaultV3 Specification
The vault code has been designed as an unopinionated system to distribute funds of depositors into different opportunities (aka strategies) and manage accounting in a robust way. That's all.

The depositors receive shares of the different investments that can then be redeemed or used as yield-bearing tokens.

The Vault does not have a preference on any of the dimensions that should be considered:
- *Decentralization*: roles can be filled by EOA, smart contract like multisig or governance module
- *Liquidity*: vault can have 0 liquidity or be fully liquid. It will depend on parameters and strategies added
- *Security*: vault managers can choose what strategies to add and how to do that process
- *Automation*: all the required actions to maintain the vault can be called by bots or manually, depending on periphery implementation

The compromises will come with the implementation of periphery contracts fulfilling the roles in the Vault.

This allows different players to deploy their own version and implement their own periphery contracts (or not use any at all)

```
Example periphery contracts: 
- Emergency module: it receives deposits of Vault Shares and allows the contract to call the shutdown function after a certain % of total Vault Shares have been deposited
- Debt Allocator: a smart contract that incentivises APY / debt allocation optimisation by rewarding the best debt allocation (see [yStarkDebtAllocator](https://github.com/jmonteer/ystarkdebtallocator))
- Strategy Staking Module: a smart contract that allows players to sponsor specific strategies (so that they are added to the vault) by staking their YFI, making money if they do well and lossing money if they don't
- ...
```
## Deployment
We expect all the vaults available to be deployed from a Factory Contract, publicly available and callable. 

Players deploying "branded" vaults (e.g. Yearn) will use a separate registry to allow permissioned endorsement of vaults for their product

When deploying a new vault, it requires the following parameters:
- asset
- name
- symbol
- role_manager

## Normal Operation

### Deposits / Mints
Users can deposit ASSET tokens to receive yvTokens (SHARES). 

Deposits are limited under depositLimit and shutdown parameters. Read below for details.

### Withdrawals / Redeems
Users can redeem their shares at any point in time if there is liquidity available. 

The redeem function will check if there are enough idle funds to serve the request. If there are not enough, it will revert. 

Optionally, a user can specify a list of strategies to withdraw from. If a list of strategies is passed, the vault will try to withdraw from them.

If not enough funds have been recovered to honor the full request, the transaction will revert.

### Vault Shares
Vault shares are ERC20 transferable yield-bearing tokens.

They are ERC4626 compliant. Please read [ERC4626 compliance](https://hackmd.io/cOFvpyR-SxWArfthhLJb5g#ERC4626-compliance) to understand the implications. 

### Accounting
The vault will evaluate profit and losses from the strategies. 

This is done comparing the current debt of the strategy with the total assets the strategy is reporting to have. 

If totalAssets < currentDebt: the vault will record a loss
If totalAssets > currentDebt: the vault will record a profit

Both loss and profit will impact strategy's debt, increasing the debt (current debt + profit) if there are profits, decreasing its debt (current debt - loss) if there are losses.

#### Fees
Fee assessment and distribution is handled by the accountant module. 

It will report the amount of fees that need to be charged and the vault will issue shares for that amount of fees.

### Profit distribution 
Profit from different processReport calls will accumulate in a buffer. This buffer will be linearly unlocked over the unlocking seconds. 

Profits will be locked for a max period of time of PROFIT_MAX_UNLOCK_TIME seconds and will be gradually distributed. To avoid spending too much gas for profit unlock, the amount of time a profit will be locked is a weighted average between the new profit and the previous profit. 

Losses will be offset by locked profit, if possible.

Issue of new shares due to fees will also unlock profit so that pps does not go down. 

Both of this offsets will prevent frontrunning (as the profit was already earned and was not distributed yet)

## Vault Management
Vault management is split in two fields: strategy management and debt management

### Strategy Management
This responsibility is taken by callers with STRATEGY_MANAGER role

A vault can have strategies added, removed and migrated 

Added strategies will be eligible to receive funds from the vault. 

Revoked strategies will return all debt and stop being eligible to receive more. 

Strategy migration is the process of replacing an existing strategy with a new one, which will inherit all parameters and debt


### Debt Management
This responsibility is taken by callers with DEBT_MANAGER role

#### Setting minimum idle funds
The debt manager can specify how many funds the vault should try to have reserved to serve withdrawal requests

These funds will remain in the vault unless requested by a Depositor

#### Setting maximum debt for a specific strategy
The maximum amount of tokens the vault will allow a strategy to owe. 


#### Rebalance Debt
The vault sends and receives funds to/from strategies. The function updateDebt(strategy, target_debt) will compare the current debt with the target_debt and cap it to max_debt for that strategy.

If the strategy currently has less debt than the target_debt, the vault will send funds to it.

The vault checks that the minimumTotalIdle parameter is respected (i.e. there's at least a certain amount of funds in the vault).

If the strategy has more debt than the maxDebt, the vault will request the funds back. These funds may be locked in the strategy, which will result in the strategy returning less funds than requested by the vault. 

## Roles
Vault functions that are permissioned will be callable by accounts that hold specific roles. 

These are: 
- STRATEGY_MANAGER: role for accounts that can add, remove or migrate strategies
- DEBT_MANAGER: role for accounts that can rebalance and manage debt related params
- EMERGENCY_MANAGER: role for accounts that can activate the shutdown mode
- ACCOUNTING_MANAGER: role for accounts that can process reports (save strategy p&l) and change accountant parameters

Every role can be filled by an EOA, multisig or other smart contracts. Each role can be filled by several accounts.

The account that manages roles is a single account, set in `role_manager`. 

This role_manager can be an EOA, a multisig or a Governance Module that relays calls. 

## Strategy Minimum API
Strategies are completely independent smart contracts that can be implemented following the proposed template or in any other way.

In any case, to be compatible with the vault, they need to implement the following functions, which are a subset of ERC4626 vaults: 
- asset(): view returning underlying asset
- vault(): view returning vault this strategy is plugged to
- totalAssets(): view returning current amount of assets. It can include rewards valued in `asset` ¡
- maxDeposit(address): view returning the amount max that the strategy can take safely
- deposit(assets, receiver): deposits `assets` amount of tokens into the strategy. it can be restricted to vault only or be open
- maxWithdraw(address): view returning how many asset can the vault take from the vault at any given point in time
- withdraw(assets, receiver, owner): withdraws `assets` amount of tokens from the strategy
- balanceOf(address): return the number of shares of the strategy that the address has

This means that the vault can deposit into any ERC4626 vault but also that a non-compliant strategy can be implemented provided that these functions have been implemented. 

Anything else is left to the strategy writer. However, to make security review easier, the Yearn's template has the following optional functions: 
- tend(): a function that will be called by bots. It will do anything to maintain a position, act on certain triggers, ...
- tendTrigger(): implementation that trigger bots that will call tend function on the contract
- invest(): deposit funds into underlying protocol
- emergencyFreeFunds(): close the position and return funds to the strategy. Losses might be accepted here.
- ...


## ERC4626 compliance
Vault Shares are ERC4626 compliant. 

The most important implication is that `withdraw` and `redeem` functions as presented in ERC4626, the liquidity to redeem shares will just be the one in the vault. No strategies will be passed to the redeem function to withdraw from with the ERC4626 compliant `withdraw` and `redeem` function. 

## Emergency Operation

### Shutdown mode
In the case the current roles stop fulfilling their responsibilities or something else happens, the EMERGENCY_MANAGER can shutdown the vault.

The shutdown mode should be the last option in an emergency as it is irreversible. 

### Deposits
_Light emergency_: Deposits can be paused by setting depositLimit to 0

_Shutdown mode_: Deposits are not allowed

### Withdrawals
Withdrawals can't be paused under any circumstance by any role

### Accounting
Shutdown mode does not affect accounting.

### Debt rebalance
_Light emergency_: Setting minimumTotalIdle to MAX_UINT256 will result in the vault requesting the debt back from strategies. This would stop new strategies from getting funded too, as the vault prioritizes minimumTotalIdle

_Shutdown mode_: All strategies' maxDebt is set to 0. Strategies will return funds as soon as they can.


### Relevant emergency
In the case the current roles stop fulfilling their responsibilities or something else's happen, the EMERGENCY_MANAGER can shutdown the vault. 

The shutdown mode should be the last option in an emergency as it is irreversible. 

During shutdown mode, the vault will try to get funds back from every strategy as soon as possible. 

No strategies can be added during shutdown

Any relevant role will start pointing to the EMERGENCY_MANAGER in case new permissioned allowed actions need to be taken.

TODO: keep it irreversible?

TODO: emergencyFreeFunds: implement a way to force wind down of a strategy (even taking losses) only callable by EMERGENCY_MANAGER?

# Yearn Registry Specification

TODO
