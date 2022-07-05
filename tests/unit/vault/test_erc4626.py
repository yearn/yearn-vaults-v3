import ape
import pytest
from utils import actions
from utils.constants import ROLES


def test_total_assets(asset, fish, fish_amount, create_vault):
    vault = create_vault(asset)

    actions.user_deposit(fish, vault, asset, fish_amount)

    assert vault.totalAssets() == fish_amount


def test_convert_to_shares(asset, fish, fish_amount, create_vault):
    vault = create_vault(asset)
    assets = fish_amount
    shares = assets

    actions.user_deposit(fish, vault, asset, assets)

    assert vault.convertToShares(assets) == shares


def test_convert_to_assets(asset, fish, fish_amount, create_vault):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares

    actions.user_deposit(fish, vault, asset, assets)

    assert vault.convertToAssets(shares) == assets


def test_preview_deposit(asset, fish, fish_amount, create_vault):
    vault = create_vault(asset)
    assets = fish_amount

    actions.user_deposit(fish, vault, asset, assets)

    assert vault.previewDeposit(assets) == assets


@pytest.mark.parametrize("deposit_limit", [10**18 // 2, 10**18])
def test_max_deposit__with_total_assets_greater_than_or_equal_deposit_limit__returns_zero(
    asset, fish, fish_amount, gov, create_vault, deposit_limit
):
    vault = create_vault(asset)
    assets = fish_amount

    actions.user_deposit(fish, vault, asset, assets)

    vault.setDepositLimit(deposit_limit, sender=gov)

    assert vault.maxDeposit(fish.address) == 0


def test_max_deposit__with_total_assets_less_than_deposit_limit__returns_net_deposit_limit(
    asset, fish, fish_amount, gov, create_vault
):
    vault = create_vault(asset)
    assets = fish_amount
    deposit_limit = assets // 2

    vault.setDepositLimit(deposit_limit, sender=gov)

    assert vault.maxDeposit(fish.address) == deposit_limit


def test_preview_mint(asset, fish, fish_amount, create_vault):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares

    actions.user_deposit(fish, vault, asset, assets)

    assert vault.previewMint(shares) == shares


@pytest.mark.parametrize("deposit_limit", [10**18 // 2, 10**18])
def test_max_mint__with_total_assets_greater_than_or_equal_deposit_limit__returns_zero(
    asset, fish, fish_amount, gov, create_vault, deposit_limit
):
    vault = create_vault(asset)
    assets = fish_amount

    actions.user_deposit(fish, vault, asset, assets)

    vault.setDepositLimit(deposit_limit, sender=gov)

    assert vault.maxMint(fish.address) == 0


def test_max_mint__with_total_assets_less_than_deposit_limit__returns_net_deposit_limit(
    asset, fish, fish_amount, gov, create_vault
):
    vault = create_vault(asset)
    assets = fish_amount
    deposit_limit = assets // 2

    vault.setDepositLimit(deposit_limit, sender=gov)

    assert vault.maxMint(fish.address) == deposit_limit


def test_preview_withdraw(asset, fish, fish_amount, create_vault):
    vault = create_vault(asset)
    assets = fish_amount
    shares = assets

    actions.user_deposit(fish, vault, asset, assets)

    assert vault.previewWithdraw(assets) == shares


def test_max_withdraw__with_balance_greater_than_total_idle__returns_total_idle(
    gov, fish, fish_amount, asset, create_vault, create_strategy
):
    vault = create_vault(asset)
    assets = fish_amount
    strategy = create_strategy(vault)
    strategy_deposit = assets // 2
    total_idle = assets - strategy_deposit

    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    actions.user_deposit(fish, vault, asset, assets)
    actions.add_strategy_to_vault(gov, strategy, vault)
    actions.add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    assert vault.maxWithdraw(fish.address) == total_idle


def test_max_withdraw__with_balance_less_than_or_equal_to_total_idle__returns_balance(
    fish, fish_amount, create_vault, asset
):
    vault = create_vault(asset)
    assets = fish_amount

    actions.user_deposit(fish, vault, asset, assets)

    assert vault.maxWithdraw(fish.address) == assets


def test_preview_redeem(asset, fish, fish_amount, create_vault):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares

    actions.user_deposit(fish, vault, asset, assets)

    assert vault.previewRedeem(shares) == assets


def test_max_redeem__with_balance_greater_than_total_idle__returns_total_idle(
    asset, fish, fish_amount, gov, create_vault, create_strategy
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares
    strategy = create_strategy(vault)
    strategy_deposit = assets // 2
    total_idle = assets - strategy_deposit

    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    actions.user_deposit(fish, vault, asset, assets)
    actions.add_strategy_to_vault(gov, strategy, vault)
    actions.add_debt_to_strategy(gov, strategy, vault, strategy_deposit)

    assert vault.maxWithdraw(fish.address) == total_idle


def test_max_redeem__with_balance_less_than_or_equal_to_total_idle__returns_balance(
    asset, fish, fish_amount, create_vault
):
    vault = create_vault(asset)
    shares = fish_amount
    assets = shares

    actions.user_deposit(fish, vault, asset, shares)

    assert vault.maxWithdraw(fish.address) == assets
