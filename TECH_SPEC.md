# Yearn System Specification

### Definitions
- Asset: Any ERC20-compliant token
- Shares: ERC20-compliant token that tracks Asset balance in the vault for every distributor. Named yv<Asset_Symbol>
- Depositor: Account that holds Shares
- Strategy: Smart contract that is used to deposit in Protocols to generate yield
- Vault: ERC4626 compliant Smart contract that receives Assets from Depositors to then distribute them among the different Strategies added to the vault, managing accounting and Assets distribution. 
- Role: the different flags an Account can have in the Vault so that the Account can do certain specific actions. Can be fulfilled by a smart contract or an EOA.
- Accountant: smart contract that receives P&L reporting and returns shares and refunds to the strategy
- Limit Modules: Add on smart contracts that can control the vaults deposit and withdraw limits dynamically.

# VaultV3 Specification
The Vault code has been designed as an non-opinionated system to distribute funds of depositors into different opportunities (aka Strategies) and manage accounting in a robust way. That's all.

Depositors receive shares (aka vaults tokens) proportional to their deposit amount. Vault tokens are yield-bearing and can be redeemed at any time to get back deposit plus any yield generated.

The Vault does not have a preference on any of the dimensions that should be considered when operating a vault:
- *Decentralization*: Roles can be filled by any address (e.g. EOA, smart contract, multi-sig).
- *Liquidity*: Vault can have 0 liquidity or be fully liquid. It will depend on parameters and strategies added.
- *Security*: Vault managers can choose what strategies to add and how to do that process.
- *Automation*: All the required actions to maintain the vault can be called by bots or manually, depending on periphery implementation.

The compromises will come with the implementation of periphery contracts fulfilling the roles in the Vault.

This allows different players to deploy their own version and implement their own periphery contracts (or not use any at all)

```
Example periphery contracts: 
- Emergency module: it receives deposits of Vault Shares and allows the contract to call the shutdown function after a certain % of total Vault Shares have been deposited
- Debt Allocator: a smart contract that incentivize's APY / debt allocation optimization by rewarding the best debt allocation (see [yStarkDebtAllocator](https://github.com/jmonteer/ystarkdebtallocator))
- Strategy Staking Module: a smart contract that allows players to sponsor specific strategies (so that they are added to the vault) by staking their YFI, making money if they do well and losing money if they don't.
- Deposit Limit Module: Will dynamically adjust the deposit limit based on the depositor and arbitrary conditions.
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

Deposits are limited under depositLimit/depositLimitModule and shutdown parameters. Read below for details.

### Withdrawals / Redeems
Users can redeem their shares at any point in time if there is liquidity available. 

Optionally, if the vault management allows, a user can specify a list of strategies to withdraw from. If a list of strategies is passed, the vault will try to withdraw from them.

If a user passed array is not defined or the use_default_queue flag has been turned on, the redeem function will use the default_queue.

In order to properly comply with the ERC-4626 standard and still allow losses, both withdraw and redeem have an additional optional parameter of 'max_loss' that can be used. The default for 'max_loss' is 0 (i.e. revert if any loss) for withdraws, and 10_000 (100%) for redeems.

If not enough funds have been recovered to honor the full request within the maxLoss, the transaction will revert.

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

Issue of new shares due to fees will also unlock profit so that PPS does not go down. 

Both of this offsets will prevent front running (as the profit was already earned and was not distributed yet)

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
- QUEUE_MANAGER: role that can set the default withdrawal queue.
- REPORTING_MANAGER: role that calls report for strategies
- DEBT_MANAGER: role that adds and removes debt from strategies
- MAX_DEBT_MANAGER: role that can set the max debt for a strategy
- DEPOSIT_LIMIT_MANAGER: role that sets deposit limit or deposit limit module for the vault
- WITHDRAW_LIMIT_MANAGER: role that sets the withdraw limit module for the vault.
- MINIMUM_IDLE_MANAGER: role that sets the minimum total idle the vault should keep
- PROFIT_UNLOCK_MANAGER: role that sets the profit_max_unlock_time
- DEBT_PURCHASER # can purchase bad debt from the vault
- EMERGENCY_MANAGER: role that can shutdown vault in an emergency

Every role can be filled by an EOA, multi-sig or other smart contracts. Each role can be filled by several accounts.

The account that manages roles is a single account, set in `role_manager`.

This role_manager can be an EOA, a multi-sig or a Governance Module that relays calls. 

The vault comes with the ability to "open" every role. Meaning that any function that requires the caller to hold that role would be come permsissionless.

The vault imposes no restrictions on the role managers ability to open or close any role. **But this should be done with extreme care as most of the roles are not meant to be opened and can lead to loss of funds if done incorrectly**.

### Strategy Management
This responsibility is taken by callers with ADD_STRATEGY_MANAGER, REVOKE_STRATEGY_MANAGER and FORCE_REVOKE_MANAGER roles

A vault can have strategies added, removed or forcefully removed 

Added strategies will be eligible to receive funds from the vault, when the max_debt is set to > 0

Revoked strategies will return all debt and stop being eligible to receive more. It can only be done when the strategy's current_debt is 0

Force revoking a strategy is only used in cases of a faulty strategy that cannot otherwise have its current_debt reduced to 0. Force revoking a strategy will result in a loss being reported by the vault.

#### Setting the modules/periphery contracts
The accountant can be set by the ACCOUNTANT_MANAGER.

A deposit_limit_module can be set by the DEPOSIT_LIMIT_MANAGER

A withdraw_limit_module can be set by the WITHDRAW_LIMIT_MANAGER

These contracts are not needed for the vault to function but are optional add ons for optimal use.

#### Reporting profits
The REPORTING_MANAGER is in charge of calling process_report() for each strategy in the vault according to its own timeline

This call will do the necessary accounting and profit locking for the individual strategy as well as charging fees

### Debt Management
This responsibility is taken by callers with DEBT_MANAGER role

This role can increase or decrease strategies specific debt.

The vault sends and receives funds to/from strategies. The function update_debt(strategy, target_debt, max_loss) (max_loss defaults to 100%) will set the current_debt of the strategy to target_debt (if possible)

If the strategy currently has less debt than the target_debt, the vault will send funds to it.

The vault checks that the `minimumTotalIdle` parameter is respected (i.e. there's at least a certain amount of funds in the vault).

If the strategy has more debt than the max_debt, the vault will request the funds back. These funds may be locked in the strategy, which will result in the strategy returning less funds than requested by the vault. 

#### Setting maximum debt for a specific strategy
The MAX_DEBT_MANAGER can set the maximum amount of tokens the vault will allow a strategy to owe at any moment in time.

Stored in strategies[strategy].max_debt

When a debt re-balance is triggered, the Vault will cap the new target debt to this number (max_debt)

#### Setting the deposit limit
The DEPOSIT_LIMIT_MANAGER is in charge of setting the deposit_limit or a deposit_limit_module for the vault

On deployment deposit_limit defaults to 0 and will need to be increased to make the vault functional

The deposit_limit will have to be set to MAX_UINT256 in order to set a deposit_limit_module, and the module will have to be address 0 to adjust the deposit_limit. Or the DEPOSIT_LIMIT_MANAGER can use the option `override` flags to do this in one step.

#### Setting the withdraw limit module
The WITHDRAW_LIMIT_MANAGER is in charge of setting the withdraw_limit_module for the vault

The vaults default withdraw limit is calculated based on the liquidity of its strategies. Setting a withdraw limit module will override this functionality.

#### Setting minimum idle funds
The MINIMUM_IDLE_MANAGER can specify how many funds the vault should try to have reserved to serve withdrawal requests

These funds will remain in the vault unless requested by a Depositor

It is recommended that if no queue_manager is set some amount of funds should remain idle to service withdrawals

#### Setting the profit unlock period
The PROFIT_UNLOCK_MANAGER is in charge of updating and setting the profit_max_unlock_time which controls how fast profits will unlock

This can be customized based on the vault based on aspects such as number of strategies, TVL, expected returns etc.

#### Setting the default queue
The QUEUE_MANAGER has the option to set a custom default_queue if desired. The vault will arrange the default queue automatically based only on the order that strategies were added to the vault. If a different order is desired the queue manager role can set a custom queue.

All strategies in the default queue must have been previously added to the vault.

The QUEUE_MANAGER can also set the use_default_queue flag, which will cause the default_queue to be used during every withdraw even if a custom_queue is passed in.

#### Buying Debt
The DEBT_PURCHASER role can buy bad debt from the vault in return for the equal amount of `asset`.

This should only ever be used in emergencies where governance wants to purchase a set amount of bad debt from the vault in order to not report a loss.

#### Shutting down the vault
In an emergency the EMERGENCY_MANAGER can shutdown the vault

This will also give the EMERGENCY_MANAGER the DEBT_MANAGER roles as well so funds can start to be returned from the strategies

## Strategy Minimum API
Strategies are completely independent smart contracts that can be implemented following the [Tokenized Strategy](https://github.com/yearn/tokenized-strategy) template or in any other way.

In any case, to be compatible with the vault, they need to implement the following functions, which are a subset of ERC4626 vaults: 
- asset(): view returning underlying asset
- maxDeposit(address): view returning the amount max that the strategy can take safely
- deposit(assets, receiver): deposits `assets` amount of tokens into the strategy. it can be restricted to vault only or be open
- maxRedeem(owner): return the max amount of shares that `owner` can redeem.
- redeem(shares, receiver, owner): redeems `shares` of the strategy for the underlying asset.
- balanceOf(address): return the number of shares of the strategy that the address has
- convertToAssets(shares): Converts `shares` into the corresponding amount of asset.
- convertToShares(assets): Converts `assets` into the corresponding amount of shares.
- previewWithdraw(assets): Converts `assets` into the corresponding amount of shares rounding up.


This means that the vault can deposit into any ERC4626 vault but also that a non-compliant strategy can be implemented provided that these functions have been implemented (even in a non ERC4626 compliant way). 

## ERC4626 compliance
Vault Shares are ERC4626 compliant. 

The most important implication is that `withdraw` and `redeem` functions as presented in ERC4626, with the ability to add two additional non-standard options.

1. max_loss: The amount in basis points that the withdrawer will accept as a loss. I.E. 100 = 1% loss accepted.
2. strategies: This is an array of strategies to use as the withdrawal queue instead of the default queue.

* `maxWithdraw` and `maxRedeem` also come with both of these optional parameters to get the most exact amounts.

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

### Debt re-balance
_Light emergency_: Setting minimumTotalIdle to MAX_UINT256 will result in the vault requesting the debt back from strategies. This would stop new strategies from getting funded too, as the vault prioritizes minimumTotalIdle

_Shutdown mode_: All strategies maxDebt is set to 0. Strategies will return funds as soon as they can.

### Relevant emergency
In the case the current roles stop fulfilling their responsibilities or something else happens, the EMERGENCY_MANAGER can shutdown the vault. 

The shutdown mode should be the last option in an emergency as it is irreversible. 

During shutdown mode, the vault will try to get funds back from every strategy as soon as possible. 

No strategies can be added during shutdown

Any relevant role will start pointing to the EMERGENCY_MANAGER in case new permissioned allowed actions need to be taken.
