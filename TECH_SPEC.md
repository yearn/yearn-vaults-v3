# Yearn System Specification

### Definitions
- Asset: Any ERC20-compliant token
- Shares: ERC20-compliant token that tracks Asset balance in the vault for every distributor. Named yv<Asset_Symbol>
- Depositor: Account that holds Shares
- Strategy: Smart contract that is used to deposit in Protocols to generate yield
- Vault: ERC4626 compliant Smart contract that receives Assets from Depositors to then distribute them among the different Strategies added to the vault, managing accounting and Assets distribution. 
- Role: the different flags an Account can have in the Vault so that the Account can do certain specific actions. Can be fulfilled by a smart contract or an EOA.
- Accountant: smart contract that receives P&L reporting and returns shares and refunds to the strategy
- Queue_Manager: smart contract that can be configured by management to hold the optimal withdrawal queues for each vault

# VaultV3 Specification
The Vault code has been designed as an unopinionated system to distribute funds of depositors into different opportunities (aka Strategies) and manage accounting in a robust way. That's all.

The depositors receive shares of the the vaults token repersentative to their deposit that can then be redeemed or used as yield-bearing tokens.

The Vault does not have a preference on any of the dimensions that should be considered when operating a vault:
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
- Strategy Staking Module: a smart contract that allows players to sponsor specific strategies (so that they are added to the vault) by staking their YFI, making money if they do well and losing money if they don't
- ...
```
## Deployment
We expect all the vaults available to be deployed from a Factory Contract, publicly available and callable. 

Players deploying "branded" vaults (e.g. Yearn) will use a separate registry to allow permissioned endorsement of vaults for their product

When deploying a new vault, it requires the following parameters:
- asset: address of the ERC20 token that can be deposited in the vault
- name: name of Shares as described in ERC20
- symbol: symbol of Shares ERC20
- role_manager: account that can assign and revoke Roles
- profit_max_unlock_time: max amount of time profit will be locked before being distributed

## Normal Operation

### Deposits / Mints
Users can deposit ASSET tokens to receive yvTokens (SHARES).

Deposits are limited under depositLimit and shutdown parameters. Read below for details.

### Withdrawals / Redeems
Users can redeem their shares at any point in time if there is liquidity available. 

Optionally, a user can specify a list of strategies to withdraw from. If a list of strategies is passed, the vault will try to withdraw from them.

If a user passed array is not defined. The redeem function will check if there is a queue_manager set to get a valid withdraw queue from. If neither happens the vault will check if there are enough idle funds to serve the request. If there are not enough, it will revert. 

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
Fee assessment and distribution are handled by the Accountant module. 

It will report the amount of fees that need to be charged and the vault will issue shares for that amount of fees.

There is also an optional protocol_fee that can be charged based on the configuration of the VaultFactory.vy

### Profit distribution 
Profit from different process_report calls will accumulate in a buffer. This buffer will be linearly unlocked over the locking period seconds at profit_distribution_rate. 

Profits will be locked for a max period of time of profit_max_unlock_time seconds and will be gradually distributed. To avoid spending too much gas for profit unlock, the amount of time a profit will be locked is a weighted average between the new profit and the previous profit. 

new_locking_period = locked_profit * pending_time_to_unlock + new_profit * PROFIT_MAX_UNLOCK_TIME / (locked_profit + new_profit)
new_profit_distribution_rate = (locked_profit + new_profit) / new_locking_period

Losses will be offset by locked profit, if possible.

Issue of new shares due to fees will also unlock profit so that pps does not go down. 

Both of this offsets will prevent frontrunning (as the profit was already earned and was not distributed yet)

## Vault Management
Vault management is split into function specific roles. Each permissioned function has its own corresponding Role.

This means roles can be combined all to one address, each distributed to separate addresses or any combination in between

## Roles
Vault functions that are permissioned will be callable by accounts that hold specific roles. 

These are: 
- ADD_STRATEGY_MANAGER: role than can add strategies to the vault
- REVOKE_STRATEGY_MANAGER: role that can remove strategies from the vault
- FORCE_REVOKE_MANAGER: role that can force remove a strategy causing a loss
- ACCOUNTANT_MANAGER: role that can set the accountant that assesses fees
- QUEUE_MANAGER: role that can set the queue_manager
- REPORTING_MANAGER: role that calls report for strategies
- DEBT_MANAGER: role that adds and removes debt from strategies
- MAX_DEBT_MANAGER: role that can set the max debt for a strategy
- DEPOSIT_LIMIT_MANAGER: role that sets deposit limit for the vault
- MINIMUM_IDLE_MANAGER: role that sets the minimum total idle the vault should keep
- PROFIT_UNLOCK_MANAGER: role that sets the profit_max_unlock_time
- DEBT_PURCHASER # can purchase bad debt from the vault
- EMERGENCY_MANAGER: role that can shutdown vault in an emergency

Every role can be filled by an EOA, multisig or other smart contracts. Each role can be filled by several accounts.

The account that manages roles is a single account, set in `role_manager`.

This role_manager can be an EOA, a multisig or a Governance Module that relays calls. 

### Strategy Management
This responsibility is taken by callers with ADD_STRATEGY_MANAGER, REVOKE_STRATEGY_MANAGER and FORCE_REVOKE_MANAGER roles

A vault can have strategies added, removed oe forcefully removed 

Added strategies will be eligible to receive funds from the vault, when the max_debt is set to > 0

Revoked strategies will return all debt and stop being eligible to receive more. It can only be done when the strategy's current_debt is 0

Force revoking a strategy is only used in cases of a faulty strategy that cannot otherwise have its current_debt reduced to 0. Force revoking a strategy will result in a loss being reported by the vault.

#### Setting the periphery contracts
The accountant and the queue_manager contracts can each be set by the ACCOUNTANT_MANAGER and QUEUE_MANAGER respectfully

The contracts are not needed for the vault to function but are recommended for optimal use

#### Reporting profits
The REPORTING_MANAGER is in charge of calling process_report() for each strategy in the vault according to its own timeline

This call will do the necessary accounting and profit locking for the individual strategy as well as charging fees

### Debt Management
This responsibility is taken by callers with DEBT_MANAGER role

This role can increase or decrease strategies specific debt.

The vault sends and receives funds to/from strategies. The function updateDebt(strategy, target_debt) will set the current_debt of the strategy to target_debt (if possible)

If the strategy currently has less debt than the target_debt, the vault will send funds to it.

The vault checks that the `minimumTotalIdle` parameter is respected (i.e. there's at least a certain amount of funds in the vault).

If the strategy has more debt than the max_debt, the vault will request the funds back. These funds may be locked in the strategy, which will result in the strategy returning less funds than requested by the vault. 

#### Setting maximum debt for a specific strategy
The MAX_DEBT_MANAGER can set the maximum amount of tokens the vault will allow a strategy to owe at any moment in time.

Stored in strategies[strategy].max_debt

When a debt rebalance is triggered, the Vault will cap the new target debt to this number (max_debt)

#### Setting the deposit limit
The DEPOSIT_LIMIT_MANAGER is in charge of setting the deposit_limit for the vault

On deployment deposit_limit defaults to 0 and will need to be increased to make the vault functional

#### Setting minimum idle funds
The MINIMUM_IDLE_MANAGER can specify how many funds the vault should try to have reserved to serve withdrawal requests

These funds will remain in the vault unless requested by a Depositor

It is recommended that if no queue_manager is set some amount of funds should remain idle to service withdrawals

#### Setting the profit unlock period
The PROFIT_UNLOCK_MANAGER is in charge of updating and setting the profit_max_unlock_time which controls how fast profits will unlock

This can be customized based on the vault based on aspects such as number of strategies, TVL, expected returns etc.

#### Buying Debt
The DEBT_PURCHASER role can buy debt from the vault in return for the equal amount of `asset`.

This should only ever be used in the case where governance wants to purchase a set amount of bade debt from the vault in order to not report a loss.

It still relies on convertToShares() so will only be viable if the conversion does not reflect and large negative realized loss from the strategy.


#### Shutting down the vault
In an emergency the EMERGENCY_MANAGER can shutdown the vault

This will also give the EMERGENCY_MANAGER the DEBT_MANAGER roles as well so funds can start to be returned from the strategies

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

This means that the vault can deposit into any ERC4626 vault but also that a non-compliant strategy can be implemented provided that these functions have been implemented (even in a non ERC4626 compliant way). 

## ERC4626 compliance
Vault Shares are ERC4626 compliant. 

The most important implication is that `withdraw` and `redeem` functions as presented in ERC4626, if no queue_manager is set the liquidity to redeem shares will just be the one in the vault. No strategies will be passed to the redeem function to withdraw from with the ERC4626 compliant `withdraw` and `redeem` function. 

## Emergency Operation

### Shutdown mode
In the case the current roles stop fulfilling their responsibilities or something else happens, the EMERGENCY_MANAGER can shutdown the vault.

The shutdown mode should be the last option in an emergency as it is irreversible. 

### Deposits
_Light emergency_: Deposits can be paused by setting depositLimit to 0

_Shutdown mode_: Deposits are not allowed

### Withdrawals
Withdrawals can't be paused under any circumstance

### Accounting
Shutdown mode does not affect accounting

### Debt rebalance
_Light emergency_: Setting minimumTotalIdle to MAX_UINT256 will result in the vault requesting the debt back from strategies. This would stop new strategies from getting funded too, as the vault prioritizes minimumTotalIdle

_Shutdown mode_: All strategies' maxDebt is set to 0. Strategies will return funds as soon as they can.

### Relevant emergency
In the case the current roles stop fulfilling their responsibilities or something else's happens, the EMERGENCY_MANAGER can shutdown the vault. 

The shutdown mode should be the last option in an emergency as it is irreversible. 

During shutdown mode, the vault will try to get funds back from every strategy as soon as possible. 

No strategies can be added during shutdown

Any relevant role will start pointing to the EMERGENCY_MANAGER in case new permissioned allowed actions need to be taken.
