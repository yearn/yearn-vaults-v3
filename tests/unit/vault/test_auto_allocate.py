import ape
import pytest
from utils.constants import DAY


def test_deposit__auto_update_debt(
    asset, fish, fish_amount, gov, vault, strategy, user_deposit
):
    assets = fish_amount

    assert vault.auto_allocate() == False

    vault.set_auto_allocate(True, sender=gov)
    vault.update_max_debt_for_strategy(strategy, assets * 2, sender=gov)

    assert vault.auto_allocate()
    assert strategy.maxDeposit(vault) > assets
    assert vault.strategies(strategy)["max_debt"] > assets
    assert vault.minimum_total_idle() == 0

    assert vault.totalAssets() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == 0

    asset.approve(vault, assets, sender=fish)

    tx = vault.deposit(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 1
    event = event[0]

    assert event.strategy == strategy
    assert event.current_debt == 0
    assert event.new_debt == assets

    assert vault.totalAssets() == assets
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == assets
    assert strategy.totalAssets() == assets
    assert strategy.balanceOf(vault) == assets
    assert vault.strategies(strategy)["current_debt"] == assets
    assert vault.balanceOf(fish) == assets


def test_mint__auto_update_debt(
    asset, fish, fish_amount, gov, vault, strategy, user_deposit
):
    assets = fish_amount

    assert vault.auto_allocate() == False

    vault.set_auto_allocate(True, sender=gov)
    vault.update_max_debt_for_strategy(strategy, assets * 2, sender=gov)

    assert vault.auto_allocate()
    assert strategy.maxDeposit(vault) > assets
    assert vault.strategies(strategy)["max_debt"] > assets
    assert vault.minimum_total_idle() == 0

    assert vault.totalAssets() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == 0

    asset.approve(vault, assets, sender=fish)

    tx = vault.mint(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 1
    event = event[0]

    assert event.strategy == strategy
    assert event.current_debt == 0
    assert event.new_debt == assets

    assert vault.totalAssets() == assets
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == assets
    assert strategy.totalAssets() == assets
    assert strategy.balanceOf(vault) == assets
    assert vault.strategies(strategy)["current_debt"] == assets
    assert vault.balanceOf(fish) == assets


def test_deposit__auto_update_debt__max_debt(
    asset, fish, fish_amount, gov, vault, strategy, user_deposit
):
    assets = fish_amount
    max_debt = assets // 10

    assert vault.auto_allocate() == False

    vault.set_auto_allocate(True, sender=gov)
    vault.update_max_debt_for_strategy(strategy, max_debt, sender=gov)

    assert vault.auto_allocate()
    assert strategy.maxDeposit(vault) > assets
    assert vault.strategies(strategy)["max_debt"] < assets
    assert vault.minimum_total_idle() == 0

    assert vault.totalAssets() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == 0

    asset.approve(vault, assets, sender=fish)

    tx = vault.deposit(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 1
    event = event[0]

    assert event.strategy == strategy
    assert event.current_debt == 0
    assert event.new_debt == max_debt

    assert vault.totalAssets() == assets
    assert vault.totalIdle() == assets - max_debt
    assert vault.totalDebt() == max_debt
    assert strategy.totalAssets() == max_debt
    assert strategy.balanceOf(vault) == max_debt
    assert vault.strategies(strategy)["current_debt"] == max_debt
    assert vault.balanceOf(fish) == assets


def test_deposit__auto_update_debt__max_deposit(
    asset, fish, fish_amount, gov, vault, strategy, user_deposit
):
    assets = fish_amount
    max_deposit = assets // 10

    assert vault.auto_allocate() == False

    vault.set_auto_allocate(True, sender=gov)
    vault.update_max_debt_for_strategy(strategy, 2**256 - 1, sender=gov)
    strategy.setMaxDebt(max_deposit, sender=gov)

    assert vault.auto_allocate()
    assert strategy.maxDeposit(vault) == max_deposit
    assert vault.strategies(strategy)["max_debt"] > assets
    assert vault.minimum_total_idle() == 0

    assert vault.totalAssets() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == 0

    asset.approve(vault, assets, sender=fish)

    tx = vault.deposit(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 1
    event = event[0]

    assert event.strategy == strategy
    assert event.current_debt == 0
    assert event.new_debt == max_deposit

    assert vault.totalAssets() == assets
    assert vault.totalIdle() == assets - max_deposit
    assert vault.totalDebt() == max_deposit
    assert strategy.totalAssets() == max_deposit
    assert strategy.balanceOf(vault) == max_deposit
    assert vault.strategies(strategy)["current_debt"] == max_deposit
    assert vault.balanceOf(fish) == assets


def test_deposit__auto_update_debt__max_deposit_zero(
    asset, fish, fish_amount, gov, vault, strategy, user_deposit
):
    assets = fish_amount
    max_deposit = 0

    assert vault.auto_allocate() == False

    vault.set_auto_allocate(True, sender=gov)
    vault.update_max_debt_for_strategy(strategy, 2**256 - 1, sender=gov)
    strategy.setMaxDebt(max_deposit, sender=gov)

    assert vault.auto_allocate()
    assert strategy.maxDeposit(vault) == max_deposit
    assert vault.strategies(strategy)["max_debt"] > assets
    assert vault.minimum_total_idle() == 0

    assert vault.totalAssets() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == 0

    asset.approve(vault, assets, sender=fish)

    tx = vault.deposit(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 0

    assert vault.totalAssets() == assets
    assert vault.totalIdle() == assets - max_deposit
    assert vault.totalDebt() == max_deposit
    assert strategy.totalAssets() == max_deposit
    assert strategy.balanceOf(vault) == max_deposit
    assert vault.strategies(strategy)["current_debt"] == max_deposit
    assert vault.balanceOf(fish) == assets


def test_deposit__auto_update_debt__min_idle(
    asset, fish, fish_amount, gov, vault, strategy, user_deposit
):
    assets = fish_amount
    min_idle = assets // 10

    assert vault.auto_allocate() == False

    vault.set_auto_allocate(True, sender=gov)
    vault.update_max_debt_for_strategy(strategy, 2**256 - 1, sender=gov)
    vault.set_minimum_total_idle(min_idle, sender=gov)

    assert vault.auto_allocate()
    assert strategy.maxDeposit(vault) > assets
    assert vault.strategies(strategy)["max_debt"] > assets
    assert vault.minimum_total_idle() == min_idle

    assert vault.totalAssets() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == 0

    asset.approve(vault, assets, sender=fish)

    tx = vault.deposit(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 1
    event = event[0]

    assert event.strategy == strategy
    assert event.current_debt == 0
    assert event.new_debt == assets - min_idle

    assert vault.totalAssets() == assets
    assert vault.totalIdle() == min_idle
    assert vault.totalDebt() == assets - min_idle
    assert strategy.totalAssets() == assets - min_idle
    assert strategy.balanceOf(vault) == assets - min_idle
    assert vault.strategies(strategy)["current_debt"] == assets - min_idle
    assert vault.balanceOf(fish) == assets


def test_deposit__auto_update_debt__min_idle(
    asset, fish, fish_amount, gov, vault, strategy, user_deposit
):
    assets = fish_amount
    min_idle = assets // 10

    assert vault.auto_allocate() == False

    vault.set_auto_allocate(True, sender=gov)
    vault.update_max_debt_for_strategy(strategy, 2**256 - 1, sender=gov)
    vault.set_minimum_total_idle(min_idle, sender=gov)

    assert vault.auto_allocate()
    assert strategy.maxDeposit(vault) > assets
    assert vault.strategies(strategy)["max_debt"] > assets
    assert vault.minimum_total_idle() == min_idle

    assert vault.totalAssets() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == 0

    asset.approve(vault, assets, sender=fish)

    tx = vault.deposit(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 1
    event = event[0]

    assert event.strategy == strategy
    assert event.current_debt == 0
    assert event.new_debt == assets - min_idle

    assert vault.totalAssets() == assets
    assert vault.totalIdle() == min_idle
    assert vault.totalDebt() == assets - min_idle
    assert strategy.totalAssets() == assets - min_idle
    assert strategy.balanceOf(vault) == assets - min_idle
    assert vault.strategies(strategy)["current_debt"] == assets - min_idle
    assert vault.balanceOf(fish) == assets


def test_deposit__auto_update_debt__min_idle_not_met(
    asset, fish, fish_amount, gov, vault, strategy, user_deposit
):
    assets = fish_amount
    min_idle = assets * 2

    assert vault.auto_allocate() == False

    vault.set_auto_allocate(True, sender=gov)
    vault.update_max_debt_for_strategy(strategy, 2**256 - 1, sender=gov)
    vault.set_minimum_total_idle(min_idle, sender=gov)

    assert vault.auto_allocate()
    assert strategy.maxDeposit(vault) > assets
    assert vault.strategies(strategy)["max_debt"] > assets
    assert vault.minimum_total_idle() == min_idle

    assert vault.totalAssets() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == 0

    asset.approve(vault, assets, sender=fish)

    tx = vault.deposit(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 0

    assert vault.totalAssets() == assets
    assert vault.totalIdle() == assets
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == assets


def test_deposit__auto_update_debt__current_debt_more_than_max_debt(
    asset, fish, fish_amount, gov, vault, strategy, user_deposit
):
    assets = fish_amount // 2
    max_debt = assets

    assert vault.auto_allocate() == False

    vault.set_auto_allocate(True, sender=gov)
    vault.update_max_debt_for_strategy(strategy, max_debt, sender=gov)

    assert vault.auto_allocate()
    assert strategy.maxDeposit(vault) > assets
    assert vault.strategies(strategy)["max_debt"] == assets
    assert vault.minimum_total_idle() == 0

    assert vault.totalAssets() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
    assert strategy.totalAssets() == 0
    assert strategy.balanceOf(vault) == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    assert vault.balanceOf(fish) == 0

    asset.approve(vault, assets, sender=fish)

    tx = vault.deposit(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 1
    event = event[0]

    assert event.strategy == strategy
    assert event.current_debt == 0
    assert event.new_debt == max_debt

    assert vault.totalAssets() == assets
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == max_debt
    assert strategy.totalAssets() == max_debt
    assert strategy.balanceOf(vault) == max_debt
    assert vault.strategies(strategy)["current_debt"] == max_debt
    assert vault.balanceOf(fish) == assets

    profit = assets // 10
    # Report profit to go over max debt
    asset.mint(strategy, profit, sender=gov)
    strategy.report(sender=gov)
    vault.process_report(strategy, sender=gov)

    assert (
        vault.strategies(strategy)["current_debt"]
        > vault.strategies(strategy)["max_debt"]
    )

    asset.approve(vault, assets, sender=fish)

    tx = vault.deposit(assets, fish, sender=fish)

    event = tx.decode_logs(vault.DebtUpdated)

    assert len(event) == 0

    assert vault.totalAssets() == assets * 2 + profit
    assert vault.totalIdle() == assets
    assert vault.totalDebt() == max_debt + profit
    assert strategy.totalAssets() == max_debt + profit
    assert strategy.balanceOf(vault) == max_debt
    assert vault.strategies(strategy)["current_debt"] == max_debt + profit
    assert vault.balanceOf(fish) > assets
