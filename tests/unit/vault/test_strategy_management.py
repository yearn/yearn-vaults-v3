import ape
import pytest
from ape import chain
from utils import checks
from utils.utils import sleep
from utils.constants import ROLES, ZERO_ADDRESS, DAY


def test_add_strategy__with_valid_strategy(chain, gov, vault, create_strategy):
    new_strategy = create_strategy(vault)

    snapshot = chain.pending_timestamp
    tx = vault.add_strategy(new_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyAdded))

    assert len(event) == 1
    assert event[0].strategy == new_strategy.address

    strategy_params = vault.strategies(new_strategy)
    assert strategy_params.activation == pytest.approx(snapshot, abs=1)
    assert strategy_params.current_debt == 0
    assert strategy_params.max_debt == 0
    assert strategy_params.last_report == pytest.approx(snapshot, abs=1)


def test_add_strategy__with_zero_address__fails_with_error(gov, vault):
    with ape.reverts("strategy cannot be zero address"):
        vault.add_strategy(ZERO_ADDRESS, sender=gov)


def test_add_strategy__with_activation__fails_with_error(gov, vault, strategy):
    with ape.reverts("strategy already active"):
        vault.add_strategy(strategy.address, sender=gov)


def test_add_strategy__with_incorrect_asset__fails_with_error(
    gov, vault, create_strategy, mock_token, create_vault
):
    # create strategy with same vault but diff asset
    other_vault = create_vault(mock_token)
    mock_token_strategy = create_strategy(other_vault)

    with ape.reverts("invalid asset"):
        vault.add_strategy(mock_token_strategy.address, sender=gov)


def test_add_strategy__with_incorrect_vault__fails_with_error(
    gov, vault, asset, create_strategy, create_vault
):
    # create strategy with diff vault but same asset
    other_vault = create_vault(asset)
    strategy = create_strategy(other_vault)

    with ape.reverts("invalid vault"):
        vault.add_strategy(strategy.address, sender=gov)


def test_revoke_strategy__with_existing_strategy(gov, vault, strategy):
    tx = vault.revoke_strategy(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyRevoked))

    assert len(event) == 1
    assert event[0].strategy == strategy.address

    strategy_params = vault.strategies(strategy)
    checks.check_revoked_strategy(strategy_params)


def test_revoke_strategy__with_non_zero_debt__fails_with_error(
    gov, asset, vault, strategy, mint_and_deposit_into_vault, add_debt_to_strategy
):
    mint_and_deposit_into_vault(vault)
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance

    add_debt_to_strategy(gov, strategy, vault, new_debt)

    with ape.reverts("strategy has debt"):
        vault.revoke_strategy(strategy.address, sender=gov)


def test_revoke_strategy__with_inactive_strategy__fails_with_error(
    gov, vault, create_strategy
):
    strategy = create_strategy(vault)

    with ape.reverts("strategy not active"):
        vault.revoke_strategy(strategy.address, sender=gov)


def test_migrate_strategy__with_no_debt(chain, gov, vault, strategy, create_strategy):
    new_strategy = create_strategy(vault)
    old_strategy = strategy
    old_strategy_params = vault.strategies(old_strategy)
    old_current_debt = old_strategy_params.current_debt
    old_max_debt = old_strategy_params.max_debt
    old_activation = old_strategy_params.activation
    old_last_report = old_strategy_params.last_report

    snapshot = chain.pending_timestamp
    tx = vault.migrate_strategy(new_strategy.address, old_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyMigrated))

    assert len(event) == 1
    assert event[0].old_strategy == old_strategy.address
    assert event[0].new_strategy == new_strategy.address

    new_strategy_params = vault.strategies(new_strategy)
    assert new_strategy_params.activation == old_activation
    assert new_strategy_params.current_debt == old_current_debt
    assert new_strategy_params.max_debt == old_max_debt
    assert new_strategy_params.last_report == old_last_report

    old_strategy_params = vault.strategies(old_strategy)
    checks.check_revoked_strategy(old_strategy_params)


def test_migrate_strategy__with_existing_debt__reverts(
    gov,
    asset,
    vault,
    strategy,
    mint_and_deposit_into_vault,
    create_strategy,
    add_debt_to_strategy,
):
    mint_and_deposit_into_vault(vault)
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    old_strategy = strategy
    new_strategy = create_strategy(vault)

    add_debt_to_strategy(gov, strategy, vault, new_debt)

    with ape.reverts("old strategy has debt"):
        vault.migrate_strategy(
            new_strategy.address, old_strategy.address, False, sender=gov
        )


def test_migrate_strategy__with_existing_debt__migrates(
    gov,
    asset,
    vault,
    strategy,
    mint_and_deposit_into_vault,
    create_strategy,
    add_debt_to_strategy,
):
    mint_and_deposit_into_vault(vault)
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    old_strategy = strategy
    new_strategy = create_strategy(vault)

    add_debt_to_strategy(gov, strategy, vault, new_debt)

    old_strategy_params = vault.strategies(old_strategy)
    old_current_debt = old_strategy_params.current_debt
    old_max_debt = old_strategy_params.max_debt
    old_activation = old_strategy_params.activation
    old_last_report = old_strategy_params.last_report

    snapshot = chain.pending_timestamp
    tx = vault.migrate_strategy(new_strategy.address, old_strategy.address, sender=gov)

    event = list(tx.decode_logs(vault.StrategyMigrated))

    assert len(event) == 1
    assert event[0].old_strategy == old_strategy.address
    assert event[0].new_strategy == new_strategy.address

    new_strategy_params = vault.strategies(new_strategy)
    assert new_strategy_params.activation == old_activation
    assert new_strategy_params.current_debt == old_current_debt
    assert new_strategy_params.max_debt == old_max_debt
    assert new_strategy_params.last_report == old_last_report

    old_strategy_params = vault.strategies(old_strategy)
    checks.check_revoked_strategy(old_strategy_params)


def test_migrate_locked_strategy__with_existing_debt__reverts(
    gov,
    asset,
    user_deposit,
    create_vault,
    mint_and_deposit_into_vault,
    create_locked_strategy,
    add_strategy_to_vault,
    add_debt_to_strategy,
    fish_amount,
    fish,
):
    vault = create_vault(asset)
    locked_strategy = create_locked_strategy(vault)
    amount = fish_amount
    shares = amount

    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, locked_strategy, vault)
    add_debt_to_strategy(gov, locked_strategy, vault, amount)

    assert vault.totalAssets() == amount
    assert vault.strategies(locked_strategy).current_debt == amount

    amount_to_lock = amount // 2
    locked_strategy.setLockedFunds(amount_to_lock, DAY, sender=gov)
    assert locked_strategy.lockedBalance() == amount_to_lock

    old_strategy = locked_strategy
    new_strategy = create_locked_strategy(vault)

    with ape.reverts("strat not liquid"):
        vault.migrate_strategy(new_strategy.address, old_strategy.address, sender=gov)

    # wait the lock period of time and we should be able to migrate
    sleep(DAY + 1)

    # unlock funds
    locked_strategy.freeLockedFunds(sender=gov)

    old_strategy_params = vault.strategies(old_strategy)
    old_current_debt = old_strategy_params.current_debt
    old_max_debt = old_strategy_params.max_debt
    old_activation = old_strategy_params.activation
    old_last_report = old_strategy_params.last_report

    snapshot = chain.pending_timestamp
    tx = vault.migrate_strategy(new_strategy.address, old_strategy.address, sender=gov)

    event = list(tx.decode_logs(vault.StrategyMigrated))

    assert len(event) == 1
    assert event[0].old_strategy == old_strategy.address
    assert event[0].new_strategy == new_strategy.address

    new_strategy_params = vault.strategies(new_strategy)
    assert new_strategy_params.activation == old_activation
    assert new_strategy_params.current_debt == old_current_debt
    assert new_strategy_params.max_debt == old_max_debt
    assert new_strategy_params.last_report == old_last_report

    old_strategy_params = vault.strategies(old_strategy)
    checks.check_revoked_strategy(old_strategy_params)


def test_migrate_lossy_strategy__with_existing_debt__migrates(
    gov,
    asset,
    user_deposit,
    create_vault,
    mint_and_deposit_into_vault,
    create_lossy_strategy,
    add_strategy_to_vault,
    add_debt_to_strategy,
    fish_amount,
    fish,
):
    vault = create_vault(asset)
    lossy_strategy = create_lossy_strategy(vault)
    amount = fish_amount
    shares = amount

    vault.set_role(gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov)
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount)

    assert vault.totalAssets() == amount
    assert vault.strategies(lossy_strategy).current_debt == amount

    amount_to_loose = amount // 2
    lossy_strategy.setLoss(gov, amount_to_loose, sender=gov)
    assert asset.balanceOf(lossy_strategy.address) == amount - amount_to_loose

    old_strategy = lossy_strategy
    new_strategy = create_lossy_strategy(vault)

    old_strategy_params = vault.strategies(old_strategy)
    old_current_debt = old_strategy_params.current_debt
    old_max_debt = old_strategy_params.max_debt
    old_activation = old_strategy_params.activation
    old_last_report = old_strategy_params.last_report

    snapshot = chain.pending_timestamp
    tx = vault.migrate_strategy(new_strategy.address, old_strategy.address, sender=gov)

    event = list(tx.decode_logs(vault.StrategyMigrated))

    assert len(event) == 1
    assert event[0].old_strategy == old_strategy.address
    assert event[0].new_strategy == new_strategy.address

    # Funds should still migrate and current debt should stay the same since the loss hasn't been reported
    new_strategy_params = vault.strategies(new_strategy)
    assert new_strategy_params.activation == old_activation
    assert new_strategy_params.current_debt == old_current_debt
    assert new_strategy_params.max_debt == old_max_debt
    assert new_strategy_params.last_report == old_last_report

    old_strategy_params = vault.strategies(old_strategy)
    checks.check_revoked_strategy(old_strategy_params)


def test_migrate_strategy__with_inactive_old_strategy__fails_with_error(
    gov, vault, create_strategy
):
    old_strategy = create_strategy(vault)
    new_strategy = create_strategy(vault)

    with ape.reverts("old strategy not active"):
        vault.migrate_strategy(new_strategy.address, old_strategy.address, sender=gov)


def test_migrate_strategy__with_incorrect_vault__fails_with_error(
    gov, asset, vault, strategy, create_strategy, create_vault
):
    old_strategy = strategy
    other_vault = create_vault(asset)
    new_strategy = create_strategy(other_vault)

    with ape.reverts("invalid vault"):
        vault.migrate_strategy(new_strategy.address, old_strategy.address, sender=gov)


def test_migrate_strategy__with_incorrect_asset__fails_with_error(
    gov, vault, strategy, mock_token, create_strategy, create_vault
):
    old_strategy = strategy
    other_vault = create_vault(mock_token)
    new_strategy = create_strategy(other_vault)

    with ape.reverts("invalid asset"):
        vault.migrate_strategy(new_strategy.address, old_strategy.address, sender=gov)


def test_migrate_strategy__with_active_new_strategy__fails_with_error(
    gov, vault, strategy, create_strategy
):
    old_strategy = strategy
    new_strategy = create_strategy(vault)

    # activate strategy
    vault.add_strategy(new_strategy.address, sender=gov)

    with ape.reverts("strategy already active"):
        vault.migrate_strategy(new_strategy.address, old_strategy.address, sender=gov)


def test_migrate_strategy__with_zero_address_new_strategy__fails_with_error(
    gov, vault, strategy
):
    old_strategy = strategy
    new_strategy = ZERO_ADDRESS

    with ape.reverts("strategy cannot be zero address"):
        vault.migrate_strategy(new_strategy, old_strategy.address, sender=gov)
