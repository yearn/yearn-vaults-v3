import ape
import pytest
from utils.constants import ROLES, DAY


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
