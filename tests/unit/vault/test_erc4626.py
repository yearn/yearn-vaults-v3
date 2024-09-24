import ape
import pytest
from utils.constants import ROLES, DAY, MAX_INT, ZERO_ADDRESS


def test_total_assets(asset, fish, fish_amount, create_vault, user_deposit):
    vault = create_vault(asset)

    user_deposit(fish, vault, asset, fish_amount)

    assert vault.totalAssets() == fish_amount


def test_convert_to_shares(asset, fish, fish_amount, create_vault, user_deposit):
    vault = create_vault(asset)
    assets = fish_amount
    shares = assets

    user_deposit(fish, vault, asset, assets)

    assert vault.convertToShares(assets) == shares


def test_convert_to_assets(asset, fish, fish_amount, create_vault, user_deposit):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares

    user_deposit(fish, vault, asset, assets)

    assert vault.convertToAssets(shares) == assets


def test_preview_deposit(asset, fish, fish_amount, create_vault, user_deposit):
    vault = create_vault(asset)
    assets = fish_amount

    user_deposit(fish, vault, asset, assets)

    assert vault.previewDeposit(assets) == assets


@pytest.mark.parametrize("deposit_limit", ["half_fish_amount", "fish_amount"])
def test_max_deposit__with_total_assets_greater_than_or_equal_deposit_limit__returns_zero(
    asset, fish, fish_amount, gov, create_vault, deposit_limit, user_deposit, request
):
    vault = create_vault(asset)
    assets = fish_amount

    user_deposit(fish, vault, asset, assets)

    deposit_limit = request.getfixturevalue(deposit_limit)

    vault.set_deposit_limit(deposit_limit, sender=gov)

    assert vault.maxDeposit(fish.address) == 0


def test_max_deposit__with_total_assets_less_than_deposit_limit__returns_net_deposit_limit(
    asset, fish, fish_amount, gov, create_vault
):
    vault = create_vault(asset)
    assets = fish_amount
    deposit_limit = assets // 2

    vault.set_deposit_limit(deposit_limit, sender=gov)

    assert vault.maxDeposit(fish.address) == deposit_limit


def test_preview_mint(asset, fish, fish_amount, create_vault, user_deposit):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares

    user_deposit(fish, vault, asset, assets)

    assert vault.previewMint(shares) == shares


@pytest.mark.parametrize("deposit_limit", ["half_fish_amount", "fish_amount"])
def test_max_mint__with_total_assets_greater_than_or_equal_deposit_limit__returns_zero(
    asset, fish, fish_amount, gov, create_vault, deposit_limit, user_deposit, request
):
    vault = create_vault(asset)
    assets = fish_amount

    user_deposit(fish, vault, asset, assets)

    deposit_limit = request.getfixturevalue(deposit_limit)

    vault.set_deposit_limit(deposit_limit, sender=gov)

    assert vault.maxMint(fish.address) == 0


def test_max_mint__with_total_assets_less_than_deposit_limit__returns_net_deposit_limit(
    asset, fish, fish_amount, gov, create_vault
):
    vault = create_vault(asset)
    assets = fish_amount
    deposit_limit = assets // 2

    vault.set_deposit_limit(deposit_limit, sender=gov)

    assert vault.maxMint(fish.address) == deposit_limit


def test_preview_withdraw(asset, fish, fish_amount, create_vault, user_deposit):
    vault = create_vault(asset)
    assets = fish_amount
    shares = assets

    user_deposit(fish, vault, asset, assets)

    assert vault.previewWithdraw(assets) == shares


def test_max_withdraw__with_balance_greater_than_total_idle__returns_balance(
    gov,
    fish,
    fish_amount,
    asset,
    create_vault,
    create_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    assets = fish_amount
    strategy = create_strategy(vault)
    strategy_deposit = assets // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    assert vault.maxWithdraw(fish.address) == assets


def test_max_withdraw__with_balance_less_than_or_equal_to_total_idle__returns_balance(
    fish, fish_amount, create_vault, asset, user_deposit
):
    vault = create_vault(asset)
    assets = fish_amount

    user_deposit(fish, vault, asset, assets)

    assert vault.maxWithdraw(fish.address) == assets


def test_max_withdraw__with_custom_params(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_strategy(vault)
    strategy_deposit = assets // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    assert vault.maxWithdraw(fish.address, 22, [strategy]) == assets


def test_max_withdraw__with_lossy_strategy(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_lossy_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_lossy_strategy(vault)
    strategy_deposit = assets // 2
    loss = strategy_deposit // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    strategy.setLoss(gov.address, loss, sender=gov)

    # Should not effect the default returned value
    assert vault.maxWithdraw(fish.address, 10_000) == assets

    # Should return just idle if max_loss == 0.
    assert vault.maxWithdraw(fish.address) == total_idle


# Tests if the first strategy has no losses but the second does
# maxWithdraw will account for the first and not the second.
def test_max_withdraw__with_liquid_and_lossy_strategy(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_strategy,
    create_lossy_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategy_deposit = assets // 2
    loss = strategy_deposit // 2
    total_idle = 0

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, liquid_strategy, vault)
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, liquid_strategy, vault, strategy_deposit)
    add_debt_to_strategy(gov, lossy_strategy, vault, strategy_deposit)

    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    # With a max loss of 100% it should not effect the default returned value
    assert vault.maxWithdraw(fish.address, 10_000) == assets
    assert (
        vault.maxWithdraw(fish.address, 10_000, [liquid_strategy, lossy_strategy])
        == assets
    )

    # With a default max_loss of 0 Should return just the first strategies debt
    assert vault.maxWithdraw(fish.address) == strategy_deposit
    assert vault.maxWithdraw(fish.address, 0) == strategy_deposit
    assert (
        vault.maxWithdraw(fish.address, 0, [liquid_strategy, lossy_strategy])
        == strategy_deposit
    )
    # With a 0 max_loss but the lossy first it should return 0.
    assert vault.maxWithdraw(fish.address, 0, [lossy_strategy, liquid_strategy]) == 0


def test_max_withdraw__with_locked_strategy(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_locked_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_locked_strategy(vault)
    strategy_deposit = assets // 2
    locked = strategy_deposit // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    strategy.setLockedFunds(locked, DAY, sender=gov)

    assert vault.maxWithdraw(fish.address) == assets - locked


def test_max_withdraw__with_use_default_queue(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_strategy(vault)
    strategy_deposit = assets
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    assert vault.maxWithdraw(fish.address) == assets
    assert vault.maxWithdraw(fish.address, 22) == assets
    assert vault.maxWithdraw(fish.address, 22, [strategy]) == assets
    # Using an inactive strategy will revert.
    with ape.reverts("inactive strategy"):
        vault.maxWithdraw(fish.address, 22, [vault])

    # Set use_default_queue to true
    vault.set_use_default_queue(True, sender=gov)

    assert vault.maxWithdraw(fish.address) == assets
    assert vault.maxWithdraw(fish.address, 22) == assets
    assert vault.maxWithdraw(fish.address, 22, [strategy]) == assets
    # Even sending an inactive strategy will return the correct amount.
    assert vault.maxWithdraw(fish.address, 22, [vault]) == assets


def test_preview_redeem(asset, fish, fish_amount, create_vault, user_deposit):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares

    user_deposit(fish, vault, asset, assets)

    assert vault.previewRedeem(shares) == assets


def test_max_redeem__with_balance_greater_than_total_idle__returns_balance(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_strategy(vault)
    strategy_deposit = assets // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    assert vault.maxRedeem(fish.address) == assets


def test_max_redeem__with_balance_less_than_or_equal_to_total_idle__returns_balance(
    asset, fish, fish_amount, create_vault, user_deposit
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares

    user_deposit(fish, vault, asset, shares)

    assert vault.maxRedeem(fish.address) == assets


def test_max_redeem__with_custom_params(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_strategy(vault)
    strategy_deposit = assets // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    assert vault.maxRedeem(fish.address, 0, [strategy]) == assets


def test_max_redeem__with_lossy_strategy(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_lossy_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_lossy_strategy(vault)
    strategy_deposit = assets // 2
    loss = strategy_deposit // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    strategy.setLoss(gov.address, loss, sender=gov)

    # Should not effect the default returned value
    assert vault.maxRedeem(fish.address) == assets

    # Should return just idle if max_loss == 0.
    assert vault.maxRedeem(fish.address, 0) == total_idle


# Tests if the first strategy has no losses but the second does
# maxRedeem will account for the first and not the second.
def test_max_redeem__with_liquid_and_lossy_strategy(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_strategy,
    create_lossy_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    liquid_strategy = create_strategy(vault)
    lossy_strategy = create_lossy_strategy(vault)
    strategy_deposit = assets // 2
    loss = strategy_deposit // 2
    total_idle = 0

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, liquid_strategy, vault)
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, liquid_strategy, vault, strategy_deposit)
    add_debt_to_strategy(gov, lossy_strategy, vault, strategy_deposit)

    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    # With a max loss of 100% it should not effect the default returned value
    assert vault.maxRedeem(fish.address) == assets
    assert vault.maxRedeem(fish.address, 10_000) == assets
    assert (
        vault.maxRedeem(fish.address, 10_000, [liquid_strategy, lossy_strategy])
        == assets
    )
    assert (
        vault.maxRedeem(fish.address, 10_000, [lossy_strategy, liquid_strategy])
        == assets
    )

    # With a max_loss of 0 Should return just the first strategies debt
    assert vault.maxRedeem(fish.address, 0) == strategy_deposit
    assert (
        vault.maxRedeem(fish.address, 0, [liquid_strategy, lossy_strategy])
        == strategy_deposit
    )
    # With a 0 max_loss but the lossy first it should return 0.
    assert vault.maxRedeem(fish.address, 0, [lossy_strategy, liquid_strategy]) == 0


def test_max_redeem__with_locked_strategy(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_locked_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_locked_strategy(vault)
    strategy_deposit = assets // 2
    locked = strategy_deposit // 2
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.MAX_DEBT_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    strategy.setLockedFunds(locked, DAY, sender=gov)

    assert vault.maxRedeem(fish.address) == assets - locked


def test_max_redeem__with_use_default_queue(
    asset,
    fish,
    fish_amount,
    gov,
    create_vault,
    create_strategy,
    add_debt_to_strategy,
    add_strategy_to_vault,
    user_deposit,
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_strategy(vault)
    strategy_deposit = assets
    total_idle = assets - strategy_deposit

    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.QUEUE_MANAGER,
        sender=gov,
    )
    user_deposit(fish, vault, asset, assets)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    assert vault.maxRedeem(fish.address) == assets
    assert vault.maxRedeem(fish.address, 22) == assets
    assert vault.maxRedeem(fish.address, 22, [strategy]) == assets
    # Using an inactive strategy will revert.
    with ape.reverts("inactive strategy"):
        vault.maxRedeem(fish.address, 22, [vault])

    # Set use_default_queue to true
    vault.set_use_default_queue(True, sender=gov)

    assert vault.maxRedeem(fish.address) == assets
    assert vault.maxRedeem(fish.address, 22) == assets
    assert vault.maxRedeem(fish.address, 22, [strategy]) == assets
    # Even sending an inactive strategy will return the correct amount.
    assert vault.maxRedeem(fish.address, 22, [vault]) == assets


# With limit modules


def test_max_deposit__with_deposit_limit_module(
    asset, fish, fish_amount, gov, create_vault, deploy_limit_module, user_deposit
):
    vault = create_vault(asset, deposit_limit=0)
    limit_module = deploy_limit_module()
    assets = fish_amount

    assert vault.deposit_limit() == 0
    assert vault.maxDeposit(fish.address) == 0

    vault.set_deposit_limit(MAX_INT, sender=gov)
    vault.set_deposit_limit_module(limit_module, sender=gov)

    assert vault.deposit_limit_module() == limit_module.address
    assert vault.maxDeposit(fish.address) == MAX_INT

    new_limit = assets * 2
    limit_module.set_default_deposit_limit(new_limit, sender=gov)

    user_deposit(fish, vault, asset, assets)

    assert vault.maxDeposit(fish.address) == new_limit - assets

    # Zero address and vault address should still be 0
    assert vault.maxDeposit(ZERO_ADDRESS) == 0
    assert vault.maxDeposit(vault.address) == 0

    # If not on a whitelist it reverts.
    limit_module.set_enforce_whitelist(True, sender=gov)

    assert vault.maxDeposit(fish.address) == 0

    # If whitelisted it now works
    limit_module.set_whitelist(fish.address, sender=gov)

    assert vault.maxDeposit(fish.address) == new_limit - assets


def test_max_mint__with_deposit_limit_module(
    asset, fish, fish_amount, gov, create_vault, deploy_limit_module, user_deposit
):
    vault = create_vault(asset, deposit_limit=0)
    limit_module = deploy_limit_module()
    assets = fish_amount

    assert vault.deposit_limit() == 0
    assert vault.maxMint(fish.address) == 0

    vault.set_deposit_limit(MAX_INT, sender=gov)
    vault.set_deposit_limit_module(limit_module, sender=gov)

    assert vault.deposit_limit_module() == limit_module.address
    assert vault.maxDeposit(fish.address) == MAX_INT

    new_limit = assets * 2
    limit_module.set_default_deposit_limit(new_limit, sender=gov)

    user_deposit(fish, vault, asset, assets)

    assert vault.maxMint(fish.address) == new_limit - assets

    # Zero address and vault address should still be 0
    assert vault.maxMint(ZERO_ADDRESS) == 0
    assert vault.maxMint(vault.address) == 0

    # If not on a whitelist it reverts.
    limit_module.set_enforce_whitelist(True, sender=gov)

    assert vault.maxMint(fish.address) == 0

    # If whitelisted it now works
    limit_module.set_whitelist(fish.address, sender=gov)

    assert vault.maxMint(fish.address) == new_limit - assets


def test_max_withdraw__with_withdraw_limit_module(
    asset,
    fish,
    bunny,
    fish_amount,
    gov,
    create_vault,
    deploy_limit_module,
    user_deposit,
):
    vault = create_vault(asset)
    limit_module = deploy_limit_module()
    assets = fish_amount // 2

    assert vault.maxWithdraw(fish.address) == 0

    vault.set_withdraw_limit_module(limit_module, sender=gov)

    assert vault.withdraw_limit_module() == limit_module.address
    # Max withdraw should still be 0
    assert vault.maxWithdraw(fish.address) == 0

    user_deposit(fish, vault, asset, assets)

    # Max should be uint max but amount is brought down based on balances.
    assert limit_module.default_withdraw_limit() == MAX_INT
    assert vault.maxWithdraw(fish.address) == assets
    assert vault.maxWithdraw(bunny.address) == 0

    new_limit = assets * 2
    limit_module.set_default_withdraw_limit(new_limit, sender=gov)

    # Doesn't change
    assert vault.maxWithdraw(fish.address) == assets
    assert vault.maxWithdraw(fish.address, 23, [vault]) == assets
    assert vault.maxWithdraw(bunny.address) == 0

    # Set limit below the balance
    new_limit = assets // 2
    limit_module.set_default_withdraw_limit(new_limit, sender=gov)

    assert vault.maxWithdraw(fish.address) == new_limit
    assert vault.maxWithdraw(fish.address, 23, [vault]) == new_limit
    assert vault.maxWithdraw(bunny.address) == 0


def test_max_redeem__with_withdraw_limit_module(
    asset,
    fish,
    bunny,
    fish_amount,
    gov,
    create_vault,
    deploy_limit_module,
    user_deposit,
):
    vault = create_vault(asset)
    limit_module = deploy_limit_module()
    assets = fish_amount // 2

    assert vault.maxRedeem(fish.address) == 0

    vault.set_withdraw_limit_module(limit_module, sender=gov)

    assert vault.withdraw_limit_module() == limit_module.address
    # Max withdraw should still be 0
    assert vault.maxRedeem(fish.address) == 0

    user_deposit(fish, vault, asset, assets)

    # Max should be uint max but amount is brought down based on balances.
    assert limit_module.default_withdraw_limit() == MAX_INT
    assert vault.maxRedeem(fish.address) == assets
    assert vault.maxRedeem(bunny.address) == 0

    new_limit = assets * 2
    limit_module.set_default_withdraw_limit(new_limit, sender=gov)

    # Doesn't change
    assert vault.maxRedeem(fish.address) == assets
    assert vault.maxRedeem(fish.address, 23, [vault]) == assets
    assert vault.maxRedeem(bunny.address) == 0

    # Set limit below the balance
    new_limit = assets // 2
    limit_module.set_default_withdraw_limit(new_limit, sender=gov)

    assert vault.maxRedeem(fish.address) == new_limit
    assert vault.maxRedeem(fish.address, 23, [vault]) == new_limit
    assert vault.maxRedeem(bunny.address) == 0


def test_deposit__with_max_uint(
    asset, fish, fish_amount, gov, create_vault, deploy_limit_module, user_deposit
):
    vault = create_vault(asset)
    assets = fish_amount

    assert asset.balanceOf(fish) == fish_amount

    asset.approve(vault.address, assets, sender=fish)

    # Should go through now
    tx = vault.deposit(MAX_INT, fish.address, sender=fish)

    event = list(tx.decode_logs(vault.Deposit))[0]

    assert event.assets == assets
    assert event.shares == assets
    assert event.owner == fish
    assert event.sender == fish
    assert vault.balanceOf(fish.address) == assets
    assert asset.balanceOf(vault.address) == assets


def test_deposit__with_deposit_limit_module(
    asset, fish, fish_amount, gov, create_vault, deploy_limit_module, user_deposit
):
    vault = create_vault(asset, deposit_limit=0)
    limit_module = deploy_limit_module()
    assets = fish_amount

    asset.approve(vault.address, assets, sender=fish)

    vault.set_deposit_limit(MAX_INT, sender=gov)
    vault.set_deposit_limit_module(limit_module, sender=gov)

    # If not on a whitelist it reverts.
    limit_module.set_enforce_whitelist(True, sender=gov)

    assert vault.maxDeposit(fish.address) == 0

    with ape.reverts("exceed deposit limit"):
        vault.deposit(assets, fish.address, sender=fish)

    # If whitelisted it now works
    limit_module.set_whitelist(fish.address, sender=gov)
    assert vault.maxDeposit(fish.address) == MAX_INT

    # Should go through now
    tx = vault.deposit(assets, fish.address, sender=fish)

    event = list(tx.decode_logs(vault.Deposit))[0]

    assert event.assets == assets
    assert event.shares == assets
    assert event.owner == fish
    assert event.sender == fish
    assert vault.balanceOf(fish.address) == assets
    assert asset.balanceOf(vault.address) == assets


def test_mint__with_deposit_limit_module(
    asset, fish, fish_amount, gov, create_vault, deploy_limit_module, user_deposit
):
    vault = create_vault(asset, deposit_limit=0)
    limit_module = deploy_limit_module()
    assets = fish_amount

    asset.approve(vault.address, assets, sender=fish)

    vault.set_deposit_limit(MAX_INT, sender=gov)
    vault.set_deposit_limit_module(limit_module, sender=gov)

    # If not on a whitelist it reverts.
    limit_module.set_enforce_whitelist(True, sender=gov)

    assert vault.maxMint(fish.address) == 0

    with ape.reverts("exceed deposit limit"):
        vault.mint(assets, fish.address, sender=fish)

    # If whitelisted it now works
    limit_module.set_whitelist(fish.address, sender=gov)
    assert vault.maxMint(fish.address) == MAX_INT

    # Should go through now
    tx = vault.mint(assets, fish.address, sender=fish)

    event = list(tx.decode_logs(vault.Deposit))[0]

    assert event.assets == assets
    assert event.shares == assets
    assert event.owner == fish
    assert event.sender == fish
    assert vault.balanceOf(fish.address) == assets
    assert asset.balanceOf(vault.address) == assets


def test_withdraw__with_withdraw_limit_module(
    asset, fish, fish_amount, gov, create_vault, deploy_limit_module, user_deposit
):
    vault = create_vault(asset)
    limit_module = deploy_limit_module()
    assets = fish_amount

    user_deposit(fish, vault, asset, assets)

    vault.set_withdraw_limit_module(limit_module, sender=gov)

    assert vault.maxWithdraw(fish.address) == assets

    new_limit = 0
    limit_module.set_default_withdraw_limit(new_limit, sender=gov)

    assert vault.maxWithdraw(fish.address) == 0

    with ape.reverts("exceed withdraw limit"):
        vault.withdraw(assets, fish.address, fish.address, sender=fish)

    new_limit = assets
    limit_module.set_default_withdraw_limit(new_limit, sender=gov)

    assert vault.maxWithdraw(fish.address) == assets

    # Should go through now
    tx = vault.withdraw(assets, fish.address, fish.address, sender=fish)

    event = list(tx.decode_logs(vault.Withdraw))[0]

    assert event.assets == assets
    assert event.shares == assets
    assert event.owner == fish
    assert event.receiver == fish
    assert vault.balanceOf(fish.address) == 0
    assert asset.balanceOf(vault.address) == 0
    assert asset.balanceOf(fish.address) == assets


def test_redeem__with_withdraw_limit_module(
    asset, fish, fish_amount, gov, create_vault, deploy_limit_module, user_deposit
):
    vault = create_vault(asset)
    limit_module = deploy_limit_module()
    assets = fish_amount

    user_deposit(fish, vault, asset, assets)

    vault.set_withdraw_limit_module(limit_module, sender=gov)

    assert vault.maxRedeem(fish.address) == assets

    new_limit = 0
    limit_module.set_default_withdraw_limit(new_limit, sender=gov)

    assert vault.maxRedeem(fish.address) == 0

    with ape.reverts("exceed withdraw limit"):
        vault.redeem(assets, fish.address, fish.address, sender=fish)

    new_limit = assets
    limit_module.set_default_withdraw_limit(new_limit, sender=gov)

    assert vault.maxRedeem(fish.address) == assets

    # Should go through now
    tx = vault.redeem(assets, fish.address, fish.address, sender=fish)

    event = list(tx.decode_logs(vault.Withdraw))[0]

    assert event.assets == assets
    assert event.shares == assets
    assert event.owner == fish
    assert event.receiver == fish
    assert vault.balanceOf(fish.address) == 0
    assert asset.balanceOf(vault.address) == 0
    assert asset.balanceOf(fish.address) == assets
