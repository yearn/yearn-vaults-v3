import ape
from utils.constants import ROLES, WEEK, StrategyChangeType
from utils.utils import from_units


def test_set_open_role__by_random_account__reverts(vault, bunny):
    with ape.reverts():
        vault.set_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=bunny)


def test_close_open_role__by_random_account__reverts(vault, gov, bunny):
    vault.set_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=gov)
    assert vault.open_roles(ROLES.ADD_STRATEGY_MANAGER) == True
    with ape.reverts():
        vault.close_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=bunny)


# STRATEGY MANAGEMENT


def test_add_strategy__add_strategy_role_closed__reverts(vault, create_strategy, bunny):
    new_strategy = create_strategy(vault)
    with ape.reverts("not allowed"):
        vault.add_strategy(new_strategy, sender=bunny)


def test_revoke_strategy__revoke_strategy_role_closed__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts("not allowed"):
        vault.revoke_strategy(new_strategy, sender=bunny)


def test_force_revoke_strategy__revoke_strategy_role_closed__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)

    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts("not allowed"):
        vault.force_revoke_strategy(new_strategy, sender=bunny)


def test_add_strategy__set_add_strategy_role_open(vault, create_strategy, bunny, gov):
    new_strategy = create_strategy(vault)
    vault.set_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=gov)
    tx = vault.add_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.ADDED


def test_revoke_strategy__set_revoke_strategy_role_open(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    vault.set_open_role(ROLES.REVOKE_STRATEGY_MANAGER, sender=gov)
    tx = vault.revoke_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED


def test_force_revoke_strategy__set_revoke_strategy_role_open(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)

    vault.add_strategy(new_strategy, sender=gov)
    vault.set_open_role(ROLES.FORCE_REVOKE_MANAGER, sender=gov)
    tx = vault.force_revoke_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED


def test_add_strategy__set_add_strategy_role_open_then_close__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.set_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=gov)
    tx = vault.add_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.ADDED
    # close the role
    vault.close_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=gov)
    with ape.reverts("not allowed"):
        vault.add_strategy(new_strategy, sender=bunny)


def test_revoke_strategy__set_revoke_strategy_role_open_then_close__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    vault.set_open_role(ROLES.REVOKE_STRATEGY_MANAGER, sender=gov)
    tx = vault.revoke_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED
    # close the role
    vault.close_open_role(ROLES.REVOKE_STRATEGY_MANAGER, sender=gov)
    with ape.reverts("not allowed"):
        vault.revoke_strategy(new_strategy, sender=bunny)


def test_force_revoke_strategy__set_revoke_strategy_role_open(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)

    vault.add_strategy(new_strategy, sender=gov)
    vault.set_open_role(ROLES.FORCE_REVOKE_MANAGER, sender=gov)
    tx = vault.force_revoke_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED
    other_strategy = create_strategy(vault)
    vault.add_strategy(other_strategy, sender=gov)
    vault.close_open_role(ROLES.FORCE_REVOKE_MANAGER, sender=gov)
    with ape.reverts("not allowed"):
        vault.force_revoke_strategy(other_strategy, sender=bunny)


# REPORTING_MANAGER


def test_process_report__reporting_role_closed__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts("not allowed"):
        vault.process_report(new_strategy, sender=bunny)


def test_process_report__set_reporting_role_open(
    vault,
    create_strategy,
    asset,
    fish_amount,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    bunny,
    gov,
):
    asset.mint(bunny, fish_amount, sender=gov)
    user_deposit(bunny, vault, asset, fish_amount)
    new_strategy = create_strategy(vault)
    add_strategy_to_vault(gov, new_strategy, vault)
    add_debt_to_strategy(gov, new_strategy, vault, fish_amount)
    vault.set_open_role(ROLES.REPORTING_MANAGER, sender=gov)
    asset.mint(new_strategy, fish_amount, sender=gov)
    tx = vault.process_report(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address and event[0].gain == fish_amount


def test_process_report__set_reporting_role_open_then_close__reverts(
    vault,
    create_strategy,
    asset,
    fish_amount,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    bunny,
    gov,
):
    asset.mint(bunny, fish_amount, sender=gov)
    user_deposit(bunny, vault, asset, fish_amount)
    new_strategy = create_strategy(vault)
    add_strategy_to_vault(gov, new_strategy, vault)
    add_debt_to_strategy(gov, new_strategy, vault, fish_amount)
    vault.set_open_role(ROLES.REPORTING_MANAGER, sender=gov)
    asset.mint(new_strategy, fish_amount, sender=gov)
    tx = vault.process_report(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address and event[0].gain == fish_amount
    # close role
    vault.close_open_role(ROLES.REPORTING_MANAGER, sender=gov)
    with ape.reverts("not allowed"):
        vault.process_report(new_strategy, sender=bunny)


# PROFIT UNLOCK MANGAGER


def test_update_profit_unlock__profit_unlock_role_closed__reverts(vault, bunny):
    with ape.reverts():
        vault.set_profit_max_unlock_time(WEEK * 2, sender=bunny)


def test_update_profit_unlock__set_profit_unlock_role_role_open(vault, bunny, gov):
    vault.set_open_role(ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)
    tx = vault.set_profit_max_unlock_time(WEEK * 2, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateProfitMaxUnlockTime))
    assert len(event) == 1
    assert event[0].profit_max_unlock_time == WEEK * 2
    vault.profitMaxUnlockTime() == WEEK * 2


def test_update_profit_unlock__set_profit_unlock_role_role_open_then_close__reverts(
    vault, bunny, gov
):
    vault.set_open_role(ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)
    tx = vault.set_profit_max_unlock_time(WEEK * 2, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateProfitMaxUnlockTime))
    assert len(event) == 1
    assert event[0].profit_max_unlock_time == WEEK * 2
    assert vault.profitMaxUnlockTime() == WEEK * 2
    vault.close_open_role(ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)
    with ape.reverts():
        vault.set_profit_max_unlock_time(WEEK, sender=bunny)


# ACCOUNTING MANAGEMENT


def test_set_minimum_total_idle__minimum_idle_role_closed__reverts(vault, bunny):
    with ape.reverts("not allowed"):
        vault.set_minimum_total_idle(0, sender=bunny)


def test_set_deposit_limit__deposit_limit_role_closed__reverts(vault, bunny):
    with ape.reverts("not allowed"):
        vault.set_deposit_limit(0, sender=bunny)


def test_update_max_debt_for_strategy__max_debt_role_closed__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts("not allowed"):
        vault.update_max_debt_for_strategy(new_strategy, 0, sender=bunny)


def test_set_minimum_total_idle__set_minimum_idle_role_open(vault, bunny, gov):
    vault.set_open_role(ROLES.MINIMUM_IDLE_MANAGER, sender=gov)
    tx = vault.set_minimum_total_idle(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateMinimumTotalIdle))
    assert len(event) == 1
    assert event[0].minimum_total_idle == 0


def test_set_deposit_limit__set_deposit_limit_role_open(vault, bunny, gov):
    vault.set_open_role(ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)
    tx = vault.set_deposit_limit(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateDepositLimit))
    assert len(event) == 1
    assert event[0].deposit_limit == 0


def test_update_max_debt_for_strategy__max_debt_limit_role_open(
    vault, create_strategy, bunny, gov
):
    vault.set_open_role(ROLES.MAX_DEBT_MANAGER, sender=gov)
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    tx = vault.update_max_debt_for_strategy(new_strategy, 420, sender=bunny)
    event = list(tx.decode_logs(vault.UpdatedMaxDebtForStrategy))
    assert len(event) == 1
    assert (
        event[0].sender == bunny.address and event[0].strategy == new_strategy.address
    )
    assert event[0].new_debt == 420


def test_set_minimum_total_idle__set_minimum_idle_role_open_then_close__reverts(
    vault, bunny, gov
):
    vault.set_open_role(ROLES.MINIMUM_IDLE_MANAGER, sender=gov)
    tx = vault.set_minimum_total_idle(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateMinimumTotalIdle))
    assert len(event) == 1
    assert event[0].minimum_total_idle == 0
    # close role
    vault.close_open_role(ROLES.MINIMUM_IDLE_MANAGER, sender=gov)
    with ape.reverts("not allowed"):
        vault.set_minimum_total_idle(0, sender=bunny)


def test_set_deposit_limit__set_deposit_limit_role_open(vault, bunny, gov):
    vault.set_open_role(ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)
    tx = vault.set_deposit_limit(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateDepositLimit))
    assert len(event) == 1
    assert event[0].deposit_limit == 0
    # close role
    vault.close_open_role(ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)
    with ape.reverts("not allowed"):
        vault.set_deposit_limit(0, sender=bunny)


def test_update_max_debt_for_strategy__set_max_debt_role_open_then_close__reverts(
    vault, create_strategy, bunny, gov
):
    vault.set_open_role(ROLES.MAX_DEBT_MANAGER, sender=gov)
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    tx = vault.update_max_debt_for_strategy(new_strategy, 420, sender=bunny)
    event = list(tx.decode_logs(vault.UpdatedMaxDebtForStrategy))
    assert len(event) == 1
    assert (
        event[0].sender == bunny.address and event[0].strategy == new_strategy.address
    )
    assert event[0].new_debt == 420
    # close role
    vault.close_open_role(ROLES.MAX_DEBT_MANAGER, sender=gov)
    with ape.reverts("not allowed"):
        vault.update_max_debt_for_strategy(new_strategy, 420, sender=bunny)


# SWEEPER


def test_sweep__sweeper_role_closed__reverts(vault, mock_token, bunny):
    with ape.reverts("not allowed"):
        vault.sweep(mock_token, sender=bunny)


def test_sweep__set_sweeper_role_open(vault, fish_amount, asset, bunny, gov):
    asset.mint(vault, fish_amount, sender=gov)
    vault.set_open_role(ROLES.SWEEPER, sender=gov)
    tx = vault.sweep(asset, sender=bunny)
    event = list(tx.decode_logs(vault.Sweep))
    assert len(event) == 1
    assert event[0].token == asset.address
    assert asset.balanceOf(bunny) == fish_amount


def test_sweep__set_sweeper_role_open_then_close__reverts(
    vault, fish_amount, asset, bunny, gov
):
    asset.mint(vault, fish_amount, sender=gov)
    vault.set_open_role(ROLES.SWEEPER, sender=gov)
    tx = vault.sweep(asset, sender=bunny)
    event = list(tx.decode_logs(vault.Sweep))
    assert len(event) == 1
    assert event[0].token == asset.address
    assert asset.balanceOf(bunny) == fish_amount
    # close role
    vault.close_open_role(ROLES.SWEEPER, sender=gov)
    with ape.reverts("not allowed"):
        vault.sweep(asset, sender=bunny)


# DEBT_MANAGER


def test_update_debt__debt_role_closed__reverts(vault, create_strategy, bunny, gov):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts("not allowed"):
        vault.update_debt(new_strategy, 0, sender=bunny)


def test_update_debt__set_debt_role_open(
    vault, create_strategy, bunny, gov, mint_and_deposit_into_vault
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    vault.update_max_debt_for_strategy(new_strategy, 1338, sender=gov)
    mint_and_deposit_into_vault(vault)
    vault.set_open_role(ROLES.DEBT_MANAGER, sender=gov)
    tx = vault.update_debt(new_strategy, 1337, sender=bunny)
    event = list(tx.decode_logs(vault.DebtUpdated))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address and event[0].new_debt == 1337


def test_update_debt__set_debt_role_open_then_close__reverts(
    vault, create_strategy, bunny, gov, mint_and_deposit_into_vault
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    vault.update_max_debt_for_strategy(new_strategy, 1338, sender=gov)
    mint_and_deposit_into_vault(vault)
    vault.set_open_role(ROLES.DEBT_MANAGER, sender=gov)
    tx = vault.update_debt(new_strategy, 1337, sender=bunny)
    event = list(tx.decode_logs(vault.DebtUpdated))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address and event[0].new_debt == 1337
    # close role
    vault.close_open_role(ROLES.DEBT_MANAGER, sender=gov)
    with ape.reverts("not allowed"):
        vault.update_debt(new_strategy, 1337, sender=bunny)


# ACCOUNTANT_MANAGER


def test_set_accountant__accountant_manager_closed__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_accountant(bunny, sender=bunny)


def test_set_accountant__accountant_manager_open(gov, vault, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_open_role(ROLES.ACCOUNTANT_MANAGER, sender=gov)

    assert vault.accountant() != bunny
    vault.set_accountant(bunny, sender=bunny)
    assert vault.accountant() == bunny


def test_set_accountant__accountant_manager_open_then_close__reverts(
    gov, vault, bunny, fish
):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_open_role(ROLES.ACCOUNTANT_MANAGER, sender=gov)

    assert vault.accountant() != bunny
    vault.set_accountant(bunny, sender=bunny)
    assert vault.accountant() == bunny

    vault.close_open_role(ROLES.ACCOUNTANT_MANAGER, sender=gov)

    with ape.reverts("not allowed"):
        vault.set_accountant(fish, sender=fish)


# EMERGENCY_MANAGER


def test_shutdown_vault__emergency_role_closed__reverts(vault, bunny):
    with ape.reverts("not allowed"):
        vault.shutdown_vault(sender=bunny)


def test_shutdown_vault__set_emergency_role_open(vault, bunny, gov):
    with ape.reverts():
        vault.shutdown_vault(sender=bunny)
    vault.set_open_role(ROLES.EMERGENCY_MANAGER, sender=gov)
    tx = vault.shutdown_vault(sender=bunny)
    event = list(tx.decode_logs(vault.Shutdown))
    assert len(event) == 1


# QUEUE MANAGER


def test_set_queue_manager__queue_manager_closed__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_queue_manager(bunny, sender=bunny)


def test_set_queue_manager__queue_manager_open(gov, vault, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_open_role(ROLES.QUEUE_MANAGER, sender=gov)

    assert vault.queue_manager() != bunny
    vault.set_queue_manager(bunny, sender=bunny)
    assert vault.queue_manager() == bunny


def test_set_queue_manager__queue_manager_open_then_close__reverts(
    gov, vault, bunny, fish
):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_open_role(ROLES.QUEUE_MANAGER, sender=gov)

    assert vault.queue_manager() != bunny
    vault.set_queue_manager(bunny, sender=bunny)
    assert vault.queue_manager() == bunny

    vault.close_open_role(ROLES.QUEUE_MANAGER, sender=gov)

    with ape.reverts("not allowed"):
        vault.set_queue_manager(fish, sender=fish)
