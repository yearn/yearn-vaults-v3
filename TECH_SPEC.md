# Yearn System Specification (DRAFT)

## Definitions
- **Asset:** Any ERC20-compliant token
- **Shares:** ERC20-compliant token that tracks Asset balance in the vault for every distributor. Named yv<Asset_Symbol>
- **Depositor:** Account that holds Shares
- **Strategy:** Smart contract used to deposit in Protocols to generate yield
- **Vault:** ERC4626 compliant Smart contract that receives Assets from Depositors to distribute them among the different Strategies added to the vault, managing accounting and Assets distribution. 
- **Role:** Flags that an Account can do specific Vault actions. Can be fulfilled by a smart contract or an EOA.
- **Accountant:** Smart contract that receives P&L reporting and returns shares and refunds to the strategy

# VaultV3 Specification
The Vault code has been designed as an unopinionated system to distribute depositors funds into different opportunities (aka Strategies) and robustly manage accounting.

The depositors receive shares of the different investments that can then be redeemed or used as yield-bearing tokens.

The Vault does not have a preference on any of the dimensions that should be considered when operating a vault:
- **Decentralization**: Roles can be filled by common wallets, smart contracts like multisigs or governance modules.
- **Liquidity**: Vault can have 0 liquidity or be fully liquid. It will depend on the parameters and strategies added.
- **Security**: Vault managers can choose what strategies to add and how to do that process.
- **Automation**: All the required actions to maintain the vault can be called by bots or manually, depending on periphery implementation.

The compromises will come with implementing periphery contracts fulfilling the roles in the Vault. This allows different players to deploy their own version and implement their own periphery contracts (or not use any at all)


## Example periphery contracts: 
- **Emergency module:** Receives deposits of Vault Shares and allows the contract to call the shutdown function after a certain % of total Vault Shares have been deposited.
- **Debt Allocator:** Smart contract that incentivizes APY / debt allocation optimization by rewarding the best debt allocation (see [yStarkDebtAllocator](https://github.com/jmonteer/ystarkdebtallocator)).
- **Strategy Staking Module:** Smart contract that allows players to sponsor specific strategies (so that they are added to the vault) by staking their YFI, making money if they do well and losing money if they don't.

## Deployment
We expect all the vaults available to be deployed from a Factory Contract, publicly available and callable. 

Players deploying "branded" vaults (e.g. Yearn) will use a separate registry to allow permissioned endorsement of vaults for their product

When deploying a new vault, it requires the following parameters:
- **asset:** Address of the ERC20 token that can be deposited in the vault.
- **name:** Name of Shares as described in ERC20.
- **symbol:** Symbol of Shares ERC20.
- **role_manager:** Account that can assign and revoke Roles.
- **PROFIT_MAX_UNLOCK_TIME:** Max amount of time profit will be distributed over.

## Normal Operation

### Deposits / Mints
Users can deposit ASSET tokens to receive yvTokens (SHARES).

Deposits are limited under `depositLimit` and shutdown parameters. Read below for details.

### Withdrawals / Redeems
Users can redeem their shares at any time if there is liquidity available. 

The redeem function will check if there are enough idle funds to serve the request. If there are not enough, it will revert. 

Optionally, a user can specify a list of strategies to withdraw from. If a list of strategies is passed, the vault will try to withdraw from them.

If not enough funds have been recovered to honor the full request, the transaction will revert.

### Vault Shares
Vault shares are ERC20 transferable yield-bearing tokens.

They are ERC4626 compliant. Please read [ERC4626 compliance](https://hackmd.io/cOFvpyR-SxWArfthhLJb5g#ERC4626-compliance) to understand the implications. 

### Accounting
The vault will evaluate profit and losses from the strategies. 

This is done by comparing the current debt of the strategy with the total assets the strategy is reporting to have. 

- If `totalAssets < currentDebt`: the vault will record a loss
- If `totalAssets > currentDebt`: the vault will record a profit

Both loss and profit will impact the strategy's debt, increasing the debt (current debt + profit) if there are profits, and decreasing its debt (current debt - loss) if there are losses.

#### Fees
The Accountant module handles fee assessment and distribution. It will report the amount of fees that need to be charged, and the vault will issue shares for that amount of fees.

#### Refunds
Refunds are positive inflows for the vault, and are sent to the vault to reward it or compensate in anyway. The Accountant module will take care of them. 

An example is an insurance mechanism like different risk tranches where the accountant will send assets to the vault to compensate for losses (and, in exchange, take higher fees).

The refunds are paid in the form of vault shares and will be instantly locked (and released gradually)

### Profit distribution 
Profit from different process_report calls will accumulate in a buffer. This buffer will be linearly unlocked over the locking period seconds at profit_distribution_rate. 

Profits will be locked for a max period of PROFIT_MAX_UNLOCK_TIME seconds and will be gradually distributed. To avoid spending too much gas for profit unlock, the period that profit will be locked for is a weighted average between the new profit and the previous profit.

- `new_locking_period = locked_profit * pending_time_to_unlock + new_profit * PROFIT_MAX_UNLOCK_TIME / (locked_profit + new_profit)`
- `new_profit_distribution_rate = (locked_profit + new_profit) / new_locking_period`

Losses will be offset by locked profit, if possible. That makes frontrunning losses impossible (unless loss > locked profit)

Issue of new shares due to fees will also insta-unlock profit so that price-per-share (pps) does not go down.

Both of these offsets will prevent frontrunning (as the profit was already earned and was not distributed yet)

Instead of locking the profit, and in order to be more capital efficient (and avoid complex asset management), the vault issues shares that holds itself. Those shares are gradually burned over time (increasing pps). So instead of releasing assets, the vault will gradually burn shares.

## Vault Management
Vault management is split into two fields: strategy management and debt management

### Strategy Management
Callers take this responsibility with the `STRATEGY_MANAGER` role

A vault can have strategies added, removed and migrated 

Added strategies will be eligible to receive funds from the vault, when the max_debt is set to > 0

Revoked strategies will return all debt and stop being eligible to receive more. It can only be done when the strategy's current_debt is 0

Strategy migration is the process of replacing an existing strategy with a new one, which will inherit all parameters, including its debt

### Debt Management
Callers take this responsibility with the `DEBT_MANAGER` role

#### Setting minimum idle funds
The debt manager can specify how many funds the vault should try to have reserved to serve withdrawal requests

These funds will remain in the vault unless requested by a Depositor

#### Setting maximum debt for a specific strategy
The maximum amount of tokens the vault will allow a strategy to owe at any moment.

Stored in `strategies[strategy].max_debt`

When a debt rebalance is triggered, the Vault will cap the new target debt to this number (max_debt)

#### Rebalance Debt
The vault sends and receives funds to/from strategies. The function updateDebt(strategy, target_debt) will set the current_debt of the strategy to target_debt (if possible)

If the strategy currently has less debt than the target_debt, the vault will send funds to it.

The vault checks that the `minimumTotalIdle` parameter is respected (i.e. there's at least a certain amount of funds in the vault).

The vault will request back funds if the strategy has more debt than the `max_debt`. These funds may be locked in the strategy, which will result in the strategy returning fewer funds than requested by the vault. 

## Roles
Vault functions that are permissioned will be callable by accounts with specific roles. 

These are: 
- `STRATEGY_MANAGER:` role for accounts that can add, remove or migrate strategies
- `DEBT_MANAGER:` role for accounts that can rebalance and manage debt related params
- `EMERGENCY_MANAGER:` role for accounts that can activate the shutdown mode
- `ACCOUNTING_MANAGER:` role for accounts that can process reports (save strategy p&l) and change accountant parameters

Every role can be filled by an EOA, multisig, or other smart contracts. Each role can be filled by several accounts.

The account that manages roles is a single account, set in `role_manager`.

This `role_manager` can be an EOA, a multisig, or a Governance Module that relays calls. 

## Strategy Minimum API
Strategies are completely independent smart contracts that can be implemented following the proposed template or in any other way.

In any case, to be compatible with the vault, they need to implement the following functions, which are a subset of ERC4626 vaults: 
- `asset():` View returning underlying asset.
- `vault():` View returning vault this strategy is plugged to.
- `totalAssets():` View returning current amount of assets. It can include rewards valued in `asset`.
- `maxDeposit(address):` View returning the amount max that the strategy can take safely.
- `deposit(assets, receiver):` Deposits `assets` amount of tokens into the strategy. It can be restricted to the vault only or be open.
- `maxWithdraw(address):` View returning how many assets can the vault take from the vault at any given point in time.
- `withdraw(assets, receiver, owner):` Withdraws `assets` amount of tokens from the strategy.
- `balanceOf(address):` Return the number of shares of the strategy that the address has.

This means that the vault can deposit into any ERC4626 vault and that a non-compliant strategy can be implemented provided that these functions have been implemented (even in a non ERC4626 compliant way). 

Anything else is left to the strategy writer. However, to make security review easier, the Yearn's template has the following optional functions: 
- `tend():` a function that will be called by bots. It will do anything to maintain a position, act on certain triggers, ...
- `tendTrigger():` implementation that trigger bots that will call tend function on the contract
- `invest():` deposit funds into underlying protocol
- `emergencyFreeFunds():` close the position and return funds to the strategy. Losses might be accepted here.


## ERC4626 compliance
Vault Shares are ERC4626 compliant. 

The most important implication is that `withdraw` and `redeem` functions as presented in ERC4626, the liquidity to redeem shares will be the one in the vault. No strategies will be passed to the redeem function to withdraw from with the ERC4626 compliant `withdraw` and `redeem` function. 

## Emergency Operation

### Shutdown mode
If the current roles stop fulfilling their responsibilities or something else happens, the `EMERGENCY_MANAGER` can shut down the vault.

The shutdown mode should be the last option in an emergency, as it is irreversible. 

### Deposits
- **Light emergency:** Deposits can be paused by setting depositLimit to 0
- **Shutdown mode:** Deposits are not allowed

### Withdrawals
Withdrawals can't be paused under any circumstance.

### Accounting
Shutdown mode does not affect accounting.

### Debt rebalance
- **Light emergency**: Setting minimumTotalIdle to MAX_UINT256 will result in the vault requesting the debt back from strategies. This would stop new strategies from getting funded too, as the vault prioritizes minimumTotalIdle
- **Shutdown mode**: All strategies' `maxDebt` is set to 0. Strategies will return funds as soon as they can.

### Relevant emergency
If the current roles stop fulfilling their responsibilities or something else happens, the `EMERGENCY_MANAGER` can shut down the vault. 

The shutdown mode should be the last option in an emergency, as it is irreversible. 

During shutdown mode, the vault will try to get funds back from every strategy as soon as possible.

No strategies can be added during shutdown.

Any relevant role will start pointing to the `EMERGENCY_MANAGER` in case new permissioned allowed actions need to be taken.
