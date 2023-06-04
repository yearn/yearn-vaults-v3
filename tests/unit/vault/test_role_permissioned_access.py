import ape
from utils.constants import ROLES, WEEK, StrategyChangeType, RoleStatusChange
from utils.utils import from_units


def test_set_open_role__by_random_account__reverts(vault, bunny):
    with ape.reverts():
        vault.set_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=bunny)


def test_close_open_role__by_random_account__reverts(vault, gov, bunny):
    tx = vault.set_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.ADD_STRATEGY_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

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
    tx = vault.set_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.ADD_STRATEGY_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

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
    tx = vault.set_open_role(ROLES.REVOKE_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.REVOKE_STRATEGY_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

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
    tx = vault.set_open_role(ROLES.FORCE_REVOKE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.FORCE_REVOKE_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.force_revoke_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED


def test_add_strategy__set_add_strategy_role_open_then_close__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    tx = vault.set_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.ADD_STRATEGY_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.add_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.ADDED
    # close the role
    tx = vault.close_open_role(ROLES.ADD_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.ADD_STRATEGY_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.add_strategy(new_strategy, sender=bunny)


def test_revoke_strategy__set_revoke_strategy_role_open_then_close__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    tx = vault.set_open_role(ROLES.REVOKE_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.REVOKE_STRATEGY_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.revoke_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED

    # close the role
    tx = vault.close_open_role(ROLES.REVOKE_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.REVOKE_STRATEGY_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.revoke_strategy(new_strategy, sender=bunny)


def test_force_revoke_strategy__set_revoke_strategy_role_open(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)

    vault.add_strategy(new_strategy, sender=gov)
    tx = vault.set_open_role(ROLES.FORCE_REVOKE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.FORCE_REVOKE_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.force_revoke_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED
    other_strategy = create_strategy(vault)
    vault.add_strategy(other_strategy, sender=gov)

    tx = vault.close_open_role(ROLES.FORCE_REVOKE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.FORCE_REVOKE_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

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
    tx = vault.set_open_role(ROLES.REPORTING_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.REPORTING_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

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

    tx = vault.set_open_role(ROLES.REPORTING_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.REPORTING_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    asset.mint(new_strategy, fish_amount, sender=gov)
    tx = vault.process_report(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address and event[0].gain == fish_amount

    # close role
    tx = vault.close_open_role(ROLES.REPORTING_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.REPORTING_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.process_report(new_strategy, sender=bunny)


# PROFIT UNLOCK MANGAGER


def test_update_profit_unlock__profit_unlock_role_closed__reverts(vault, bunny):
    with ape.reverts():
        vault.set_profit_max_unlock_time(WEEK * 2, sender=bunny)


def test_update_profit_unlock__set_profit_unlock_role_role_open(vault, bunny, gov):
    tx = vault.set_open_role(ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.PROFIT_UNLOCK_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.set_profit_max_unlock_time(WEEK * 2, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateProfitMaxUnlockTime))
    assert len(event) == 1
    assert event[0].profit_max_unlock_time == WEEK * 2
    vault.profitMaxUnlockTime() == WEEK * 2


def test_update_profit_unlock__set_profit_unlock_role_role_open_then_close__reverts(
    vault, bunny, gov
):
    tx = vault.set_open_role(ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.PROFIT_UNLOCK_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.set_profit_max_unlock_time(WEEK * 2, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateProfitMaxUnlockTime))
    assert len(event) == 1
    assert event[0].profit_max_unlock_time == WEEK * 2
    assert vault.profitMaxUnlockTime() == WEEK * 2
    tx = vault.close_open_role(ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.PROFIT_UNLOCK_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

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
    tx = vault.set_open_role(ROLES.MINIMUM_IDLE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.MINIMUM_IDLE_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.set_minimum_total_idle(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateMinimumTotalIdle))
    assert len(event) == 1
    assert event[0].minimum_total_idle == 0


def test_set_deposit_limit__set_deposit_limit_role_open(vault, bunny, gov):
    tx = vault.set_open_role(ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.DEPOSIT_LIMIT_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.set_deposit_limit(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateDepositLimit))
    assert len(event) == 1
    assert event[0].deposit_limit == 0


def test_update_max_debt_for_strategy__max_debt_limit_role_open(
    vault, create_strategy, bunny, gov
):
    tx = vault.set_open_role(ROLES.MAX_DEBT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.MAX_DEBT_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

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
    tx = vault.set_open_role(ROLES.MINIMUM_IDLE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.MINIMUM_IDLE_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.set_minimum_total_idle(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateMinimumTotalIdle))
    assert len(event) == 1
    assert event[0].minimum_total_idle == 0
    # close role
    tx = vault.close_open_role(ROLES.MINIMUM_IDLE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.MINIMUM_IDLE_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.set_minimum_total_idle(0, sender=bunny)


def test_set_deposit_limit__set_deposit_limit_role_open(vault, bunny, gov):
    tx = vault.set_open_role(ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.DEPOSIT_LIMIT_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.set_deposit_limit(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateDepositLimit))
    assert len(event) == 1
    assert event[0].deposit_limit == 0
    # close role
    tx = vault.close_open_role(ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.DEPOSIT_LIMIT_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.set_deposit_limit(0, sender=bunny)


def test_update_max_debt_for_strategy__set_max_debt_role_open_then_close__reverts(
    vault, create_strategy, bunny, gov
):
    tx = vault.set_open_role(ROLES.MAX_DEBT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.MAX_DEBT_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

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
    tx = vault.close_open_role(ROLES.MAX_DEBT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.MAX_DEBT_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.update_max_debt_for_strategy(new_strategy, 420, sender=bunny)


# DEBT_PURCHASER


def test_buy_debt__debt_purchaser_role_closed__reverts(vault, strategy, bunny):
    with ape.reverts("not allowed"):
        vault.buy_debt(strategy.address, 0, sender=bunny)


def test_buy_debt__set_debt_purchaser_role_open(
    vault,
    strategy,
    mint_and_deposit_into_vault,
    add_debt_to_strategy,
    fish_amount,
    asset,
    bunny,
    gov,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, gov, amount)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # Approve vault to pull funds.
    asset.mint(bunny.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=bunny)

    tx = vault.set_open_role(ROLES.DEBT_PURCHASER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.DEBT_PURCHASER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.buy_debt(strategy.address, amount, sender=bunny)
    event = list(tx.decode_logs(vault.DebtPurchased))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].amount == amount

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == amount
    assert event[0].new_debt == 0


def test_buy_debt__set_debt_purchaser_role_open_then_close__reverts(
    vault,
    strategy,
    mint_and_deposit_into_vault,
    add_debt_to_strategy,
    fish_amount,
    asset,
    bunny,
    gov,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, gov, amount)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # Approve vault to pull funds.
    asset.mint(bunny.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=bunny)

    vault.set_open_role(ROLES.DEBT_PURCHASER, sender=gov)
    tx = vault.buy_debt(strategy.address, amount // 2, sender=bunny)
    event = list(tx.decode_logs(vault.DebtPurchased))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].amount == amount // 2

    event = list(tx.decode_logs(vault.DebtUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == amount
    assert event[0].new_debt == amount // 2
    # close role

    tx = vault.close_open_role(ROLES.DEBT_PURCHASER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.DEBT_PURCHASER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.buy_debt(strategy.address, amount // 2, sender=bunny)


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
    tx = vault.set_open_role(ROLES.DEBT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.DEBT_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

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
    tx = vault.set_open_role(ROLES.DEBT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.DEBT_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.update_debt(new_strategy, 1337, sender=bunny)
    event = list(tx.decode_logs(vault.DebtUpdated))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address and event[0].new_debt == 1337
    # close role
    tx = vault.close_open_role(ROLES.DEBT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.DEBT_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.update_debt(new_strategy, 1337, sender=bunny)


# ACCOUNTANT_MANAGER


def test_set_accountant__accountant_manager_closed__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_accountant(bunny, sender=bunny)


def test_set_accountant__accountant_manager_open(gov, vault, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    tx = vault.set_open_role(ROLES.ACCOUNTANT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.ACCOUNTANT_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    assert vault.accountant() != bunny
    vault.set_accountant(bunny, sender=bunny)
    assert vault.accountant() == bunny


def test_set_accountant__accountant_manager_open_then_close__reverts(
    gov, vault, bunny, fish
):
    # We temporarily give bunny the role of DEBT_MANAGER
    tx = vault.set_open_role(ROLES.ACCOUNTANT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.ACCOUNTANT_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    assert vault.accountant() != bunny
    vault.set_accountant(bunny, sender=bunny)
    assert vault.accountant() == bunny

    tx = vault.close_open_role(ROLES.ACCOUNTANT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.ACCOUNTANT_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.set_accountant(fish, sender=fish)


# EMERGENCY_MANAGER


def test_shutdown_vault__emergency_role_closed__reverts(vault, bunny):
    with ape.reverts("not allowed"):
        vault.shutdown_vault(sender=bunny)


def test_shutdown_vault__set_emergency_role_open(vault, bunny, gov):
    with ape.reverts():
        vault.shutdown_vault(sender=bunny)

    tx = vault.set_open_role(ROLES.EMERGENCY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.EMERGENCY_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    tx = vault.shutdown_vault(sender=bunny)
    event = list(tx.decode_logs(vault.Shutdown))
    assert len(event) == 1


# QUEUE MANAGER


def test_set_default_queue__queue_manager_closed__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_default_queue([], sender=bunny)


def test_set_default_queue__queue_manager_open(gov, vault, strategy, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    tx = vault.set_open_role(ROLES.QUEUE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.QUEUE_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    assert vault.get_default_queue() != []
    vault.set_default_queue([], sender=bunny)
    assert vault.get_default_queue() == []


def test_set_default_queue__queue_manager_open_then_close__reverts(
    gov, vault, strategy, bunny, fish
):
    # We temporarily give bunny the role of DEBT_MANAGER
    tx = vault.set_open_role(ROLES.QUEUE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.QUEUE_MANAGER
    assert event[0].status == RoleStatusChange.OPENED

    assert vault.get_default_queue() != []
    vault.set_default_queue([], sender=bunny)
    assert vault.get_default_queue() == []

    tx = vault.close_open_role(ROLES.QUEUE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleStatusChanged))
    assert len(event) == 1
    assert event[0].role == ROLES.QUEUE_MANAGER
    assert event[0].status == RoleStatusChange.CLOSED

    with ape.reverts("not allowed"):
        vault.set_default_queue([], sender=fish)
