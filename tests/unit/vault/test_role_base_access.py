import ape
from utils.constants import ROLES, WEEK, StrategyChangeType, ZERO_ADDRESS, MAX_INT
from utils.utils import days_to_secs


# STRATEGY MANAGEMENT


def test_add_strategy__no_add_strategy_manager__reverts(vault, create_strategy, bunny):
    new_strategy = create_strategy(vault)
    with ape.reverts("not allowed"):
        vault.add_strategy(new_strategy, sender=bunny)


def test_add_strategy__add_strategy_manager(vault, create_strategy, gov, bunny):
    # We temporarily give bunny the role of STRATEGY_MANAGER
    tx = vault.set_role(bunny.address, ROLES.ADD_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.ADD_STRATEGY_MANAGER

    new_strategy = create_strategy(vault)
    tx = vault.add_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.ADDED


def test_revoke_strategy__no_revoke_strategy_manager__reverts(vault, strategy, bunny):
    with ape.reverts("not allowed"):
        vault.revoke_strategy(strategy, sender=bunny)


def test_revoke_strategy__revoke_strategy_manager(vault, strategy, gov, bunny):
    # We temporarily give bunny the role of STRATEGY_MANAGER
    tx = vault.set_role(bunny.address, ROLES.REVOKE_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.REVOKE_STRATEGY_MANAGER

    tx = vault.revoke_strategy(strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED


def test_force_revoke_strategy__no_revoke_strategy_manager__reverts(
    vault, strategy, create_strategy, bunny
):

    with ape.reverts("not allowed"):
        vault.force_revoke_strategy(strategy, sender=bunny)


def test_force_revoke_strategy__revoke_strategy_manager(
    vault, strategy, create_strategy, gov, bunny
):
    # We temporarily give bunny the role of STRATEGY_MANAGER
    tx = vault.set_role(bunny.address, ROLES.FORCE_REVOKE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.FORCE_REVOKE_MANAGER

    tx = vault.force_revoke_strategy(strategy, sender=bunny)

    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED


# ACCOUNTING MANAGEMENT


def test_set_minimum_total_idle__no_min_idle_manager__reverts(bunny, vault):
    minimum_total_idle = 1
    with ape.reverts("not allowed"):
        vault.set_minimum_total_idle(minimum_total_idle, sender=bunny)


def test_set_minimum_total_idle__min_idle_manager(gov, vault, bunny):
    # We temporarily give bunny the role
    tx = vault.set_role(bunny.address, ROLES.MINIMUM_IDLE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.MINIMUM_IDLE_MANAGER

    assert vault.minimum_total_idle() == 0
    minimum_total_idle = 1
    vault.set_minimum_total_idle(minimum_total_idle, sender=bunny)
    assert vault.minimum_total_idle() == 1


def test_update_max_debt__no_max_debt_manager__reverts(vault, strategy, bunny):
    assert vault.strategies(strategy).max_debt == 0
    max_debt_for_strategy = 1
    with ape.reverts("not allowed"):
        vault.update_max_debt_for_strategy(
            strategy, max_debt_for_strategy, sender=bunny
        )


def test_update_max_debt__max_debt_manager(gov, vault, strategy, bunny):
    # We temporarily give bunny the role
    tx = vault.set_role(bunny.address, ROLES.MAX_DEBT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.MAX_DEBT_MANAGER

    assert vault.strategies(strategy).max_debt == 0
    max_debt_for_strategy = 1
    vault.update_max_debt_for_strategy(strategy, max_debt_for_strategy, sender=bunny)
    assert vault.strategies(strategy).max_debt == 1


# Deposit and Withdraw limits


def test_set_deposit_limit__no_deposit_limit_manager__reverts(bunny, vault):
    deposit_limit = 1
    with ape.reverts("not allowed"):
        vault.set_deposit_limit(deposit_limit, sender=bunny)


def test_set_deposit_limit__deposit_limit_manager(gov, vault, bunny):
    # We temporarily give bunny the role
    tx = vault.set_role(bunny.address, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.DEPOSIT_LIMIT_MANAGER

    deposit_limit = 1
    assert vault.deposit_limit() != deposit_limit
    vault.set_deposit_limit(deposit_limit, sender=bunny)
    assert vault.deposit_limit() == deposit_limit


def test_set_deposit_limit_with_limit_module__reverts(gov, vault, bunny):
    # We temporarily give bunny the role
    tx = vault.set_role(bunny.address, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.DEPOSIT_LIMIT_MANAGER

    deposit_limit = 1

    vault.set_deposit_limit_module(bunny, sender=gov)

    with ape.reverts("using module"):
        vault.set_deposit_limit(deposit_limit, sender=bunny)


def test_set_deposit_limit_with_limit_module__override(gov, vault, bunny):
    # We temporarily give bunny the role
    tx = vault.set_role(bunny.address, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.DEPOSIT_LIMIT_MANAGER

    deposit_limit = 1
    deposit_limit_module = bunny

    vault.set_deposit_limit_module(deposit_limit_module, sender=gov)

    assert vault.deposit_limit_module() == deposit_limit_module

    with ape.reverts("using module"):
        vault.set_deposit_limit(deposit_limit, sender=bunny)

    tx = vault.set_deposit_limit(deposit_limit, True, sender=bunny)

    assert vault.deposit_limit() == deposit_limit
    assert vault.deposit_limit_module() == ZERO_ADDRESS

    event = list(tx.decode_logs(vault.UpdateDepositLimitModule))

    assert len(event) == 1
    assert event[0].deposit_limit_module == ZERO_ADDRESS

    event = list(tx.decode_logs(vault.UpdateDepositLimit))

    assert len(event) == 1
    assert event[0].deposit_limit == deposit_limit


def test_set_deposit_limit_module__no_deposit_limit_manager__reverts(bunny, vault):
    deposit_limit_module = bunny
    with ape.reverts("not allowed"):
        vault.set_deposit_limit_module(deposit_limit_module, sender=bunny)


def test_set_deposit_limit_module__deposit_limit_manager(gov, vault, bunny):
    # We temporarily give bunny the role
    tx = vault.set_role(bunny.address, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.DEPOSIT_LIMIT_MANAGER

    deposit_limit_module = bunny
    assert vault.deposit_limit_module() == ZERO_ADDRESS
    tx = vault.set_deposit_limit_module(deposit_limit_module, sender=bunny)

    assert vault.deposit_limit_module() == deposit_limit_module

    event = list(tx.decode_logs(vault.UpdateDepositLimitModule))

    assert len(event) == 1
    assert event[0].deposit_limit_module == deposit_limit_module


def test_set_deposit_limit_module_with_limit__reverts(gov, vault, bunny):
    # We temporarily give bunny the role
    tx = vault.set_role(bunny.address, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.DEPOSIT_LIMIT_MANAGER

    vault.set_deposit_limit(1, sender=gov)

    with ape.reverts("using deposit limit"):
        vault.set_deposit_limit_module(bunny, sender=gov)


def test_set_deposit_limit_module_with_limit__override(gov, vault, bunny):
    # We temporarily give bunny the role
    tx = vault.set_role(bunny.address, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.DEPOSIT_LIMIT_MANAGER

    vault.set_deposit_limit(1, sender=gov)

    deposit_limit_module = bunny
    with ape.reverts("using deposit limit"):
        vault.set_deposit_limit_module(deposit_limit_module, sender=gov)

    tx = vault.set_deposit_limit_module(deposit_limit_module, True, sender=gov)

    assert vault.deposit_limit() == MAX_INT
    assert vault.deposit_limit_module() == deposit_limit_module

    event = list(tx.decode_logs(vault.UpdateDepositLimitModule))

    assert len(event) == 1
    assert event[0].deposit_limit_module == deposit_limit_module

    event = list(tx.decode_logs(vault.UpdateDepositLimit))

    assert len(event) == 1
    assert event[0].deposit_limit == MAX_INT


def test_set_withdraw_limit_module__no_withdraw_limit_manager__reverts(bunny, vault):
    withdraw_limit_module = bunny
    with ape.reverts("not allowed"):
        vault.set_withdraw_limit_module(withdraw_limit_module, sender=bunny)


def test_set_withdraw_limit_module__withdraw_limit_manager(gov, vault, bunny):
    # We temporarily give bunny the role
    tx = vault.set_role(bunny.address, ROLES.WITHDRAW_LIMIT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.WITHDRAW_LIMIT_MANAGER

    withdraw_limit_module = bunny
    assert vault.withdraw_limit_module() == ZERO_ADDRESS
    tx = vault.set_withdraw_limit_module(withdraw_limit_module, sender=bunny)

    assert vault.withdraw_limit_module() == withdraw_limit_module

    event = list(tx.decode_logs(vault.UpdateWithdrawLimitModule))

    assert len(event) == 1
    assert event[0].withdraw_limit_module == withdraw_limit_module


# DEBT_PURCHASER


def test_buy_debt__no_debt_purchaser__reverts(vault, strategy, bunny):
    with ape.reverts("not allowed"):
        vault.buy_debt(strategy, 0, sender=bunny)


def test_buy_debt__debt_purchaser(
    gov,
    asset,
    vault,
    bunny,
    strategy,
    fish_amount,
    add_debt_to_strategy,
    mint_and_deposit_into_vault,
):
    amount = fish_amount
    # We temporarily give bunny the role of ACCOUNTING_MANAGER

    vault.set_role(bunny.address, ROLES.DEBT_PURCHASER, sender=gov)

    mint_and_deposit_into_vault(vault, gov, amount)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # Approve vault to pull funds.
    asset.mint(bunny.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=bunny)

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


# DEBT_MANAGER


def test_update_debt__no_debt_manager__reverts(vault, gov, strategy, bunny):
    with ape.reverts("not allowed"):
        vault.update_debt(strategy, 10**18, sender=bunny)


def test_update_debt__debt_manager(
    gov, mint_and_deposit_into_vault, vault, strategy, bunny
):
    # We temporarily give bunny the role of DEBT_MANAGER
    tx = vault.set_role(bunny.address, ROLES.DEBT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.DEBT_MANAGER

    # Provide vault with funds
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)

    max_debt_for_strategy = 1
    vault.update_max_debt_for_strategy(strategy, max_debt_for_strategy, sender=gov)

    tx = vault.update_debt(strategy, max_debt_for_strategy, sender=bunny)

    event = list(tx.decode_logs(vault.DebtUpdated))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == 0
    assert event[0].new_debt == 1


# EMERGENCY_MANAGER


def test_shutdown_vault__no_emergency_manager__reverts(vault, bunny):
    with ape.reverts("not allowed"):
        vault.shutdown_vault(sender=bunny)


def test_shutdown_vault__emergency_manager(gov, vault, bunny):
    # We temporarily give bunny the role of EMERGENCY_MANAGER
    tx = vault.set_role(bunny.address, ROLES.EMERGENCY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.EMERGENCY_MANAGER

    assert vault.isShutdown() == False
    tx = vault.shutdown_vault(sender=bunny)

    assert vault.isShutdown() == True
    event = list(tx.decode_logs(vault.Shutdown))
    assert len(event) == 1
    # lets ensure that we give the EMERGENCY_MANAGER DEBT_MANAGER permissions after shutdown
    # EMERGENCY_MANAGER=8192 DEBT_MANGER=64 -> binary or operation should give us 8256 (100001000000)
    assert vault.roles(bunny) == 8256


# REPORTING_MANAGER


def test_process_report__no_reporting_manager__reverts(vault, strategy, bunny):
    with ape.reverts("not allowed"):
        vault.process_report(strategy, sender=bunny)


def test_process_report__reporting_manager(
    gov,
    vault,
    asset,
    airdrop_asset,
    add_debt_to_strategy,
    strategy,
    bunny,
    mint_and_deposit_into_vault,
):
    # We temporarily give bunny the role of ACCOUNTING_MANAGER
    tx = vault.set_role(bunny.address, ROLES.REPORTING_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.REPORTING_MANAGER

    # Provide liquidity into vault
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)
    # add debt to strategy
    add_debt_to_strategy(gov, strategy, vault, 2)
    # airdrop gain to strategy
    airdrop_asset(gov, asset, strategy, 1)
    strategy.report(sender=gov)

    tx = vault.process_report(strategy.address, sender=bunny)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == 1
    assert event[0].loss == 0


# SET_ACCOUNTANT_MANAGER


def test_set_accountant__no_accountant_manager__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_accountant(bunny, sender=bunny)


def test_set_accountant__accountant_manager(gov, vault, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    tx = vault.set_role(bunny.address, ROLES.ACCOUNTANT_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.ACCOUNTANT_MANAGER

    assert vault.accountant() != bunny
    vault.set_accountant(bunny, sender=bunny)
    assert vault.accountant() == bunny


# QUEUE MANAGER


def test_set_default_queue__no_queue_manager__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_default_queue([], sender=bunny)


def test_use_default_queue__no_queue_manager__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.set_use_default_queue(True, sender=bunny)


def test_set_default_queue__queue_manager(gov, vault, strategy, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    tx = vault.set_role(bunny.address, ROLES.QUEUE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.QUEUE_MANAGER

    assert vault.get_default_queue() != []
    vault.set_default_queue([], sender=bunny)
    assert vault.get_default_queue() == []


def test_set_use_default_queue__queue_manager(gov, vault, strategy, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    tx = vault.set_role(bunny.address, ROLES.QUEUE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.QUEUE_MANAGER

    assert vault.use_default_queue() == False
    tx = vault.set_use_default_queue(True, sender=bunny)

    event = list(tx.decode_logs(vault.UpdateUseDefaultQueue))
    assert len(event) == 1
    assert event[0].use_default_queue == True
    assert vault.use_default_queue() == True


# PROFIT UNLOCK MANAGER


def test_set_profit_unlock__no_profit_unlock_manager__reverts(bunny, vault):
    with ape.reverts("not allowed"):
        vault.setProfitMaxUnlockTime(WEEK // 2, sender=bunny)


def test_set_profit_unlock__profit_unlock_manager(gov, vault, bunny):
    # We temporarily give bunny the role of profit unlock manager
    tx = vault.set_role(bunny.address, ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.PROFIT_UNLOCK_MANAGER

    time = WEEK // 2
    assert vault.profitMaxUnlockTime() != time
    vault.setProfitMaxUnlockTime(time, sender=bunny)
    assert vault.profitMaxUnlockTime() == time


def test_set_profit_unlock__to_high__reverts(gov, vault, bunny):
    # We temporarily give bunny the role of profit unlock manager
    tx = vault.set_role(bunny.address, ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.PROFIT_UNLOCK_MANAGER

    time = int(1e20)
    current_time = vault.profitMaxUnlockTime()

    with ape.reverts("profit unlock time too long"):
        vault.setProfitMaxUnlockTime(time, sender=bunny)

    assert vault.profitMaxUnlockTime() == current_time


def test__add_role(gov, vault, bunny):
    assert vault.roles(bunny) == 0

    tx = vault.add_role(bunny.address, ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.PROFIT_UNLOCK_MANAGER

    assert vault.roles(bunny) == ROLES.PROFIT_UNLOCK_MANAGER

    tx = vault.add_role(bunny.address, ROLES.FORCE_REVOKE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.PROFIT_UNLOCK_MANAGER | ROLES.FORCE_REVOKE_MANAGER

    assert (
        vault.roles(bunny) == ROLES.PROFIT_UNLOCK_MANAGER | ROLES.FORCE_REVOKE_MANAGER
    )

    tx = vault.add_role(bunny.address, ROLES.REPORTING_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert (
        event[0].role
        == ROLES.PROFIT_UNLOCK_MANAGER
        | ROLES.FORCE_REVOKE_MANAGER
        | ROLES.REPORTING_MANAGER
    )

    assert (
        vault.roles(bunny)
        == ROLES.PROFIT_UNLOCK_MANAGER
        | ROLES.FORCE_REVOKE_MANAGER
        | ROLES.REPORTING_MANAGER
    )


def test__remove_role(gov, vault, bunny):
    assert vault.roles(bunny) == 0

    tx = vault.set_role(
        bunny.address,
        ROLES.PROFIT_UNLOCK_MANAGER
        | ROLES.FORCE_REVOKE_MANAGER
        | ROLES.REPORTING_MANAGER,
        sender=gov,
    )

    assert (
        vault.roles(bunny)
        == ROLES.PROFIT_UNLOCK_MANAGER
        | ROLES.FORCE_REVOKE_MANAGER
        | ROLES.REPORTING_MANAGER
    )

    tx = vault.remove_role(bunny.address, ROLES.FORCE_REVOKE_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.PROFIT_UNLOCK_MANAGER | ROLES.REPORTING_MANAGER

    assert vault.roles(bunny) == ROLES.PROFIT_UNLOCK_MANAGER | ROLES.REPORTING_MANAGER

    tx = vault.remove_role(bunny.address, ROLES.REPORTING_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == ROLES.PROFIT_UNLOCK_MANAGER

    assert vault.roles(bunny) == ROLES.PROFIT_UNLOCK_MANAGER

    tx = vault.remove_role(bunny.address, ROLES.PROFIT_UNLOCK_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == 0

    assert vault.roles(bunny) == 0


def test__add_role__wont_remove(gov, vault):
    roles = ROLES(vault.roles(gov))
    role = ROLES.MINIMUM_IDLE_MANAGER

    assert role in roles

    tx = vault.add_role(gov.address, role, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == gov.address
    assert event[0].role == roles

    assert roles == vault.roles(gov)
    assert role in ROLES(vault.roles(gov))

    # Make sure we can set min idle.
    vault.set_minimum_total_idle(100, sender=gov)

    assert vault.minimum_total_idle() == 100


def test__remove_role__wont_add(gov, vault, bunny, strategy):
    assert vault.roles(bunny) == 0

    tx = vault.remove_role(bunny.address, ROLES.ADD_STRATEGY_MANAGER, sender=gov)

    event = list(tx.decode_logs(vault.RoleSet))
    assert len(event) == 1
    assert event[0].account == bunny.address
    assert event[0].role == 0

    assert vault.roles(bunny) == 0

    with ape.reverts("not allowed"):
        vault.add_strategy(strategy, sender=bunny)


def test__set_name(gov, vault, bunny):
    name = vault.name()
    new_name = "New Vault Name"

    with ape.reverts("not allowed"):
        vault.setName(new_name, sender=bunny)

    vault.set_role(bunny, ROLES.ALL, sender=gov)

    with ape.reverts("not allowed"):
        vault.setName(new_name, sender=bunny)

    assert vault.name() != new_name

    vault.setName(new_name, sender=gov)

    assert vault.name() == new_name
    assert vault.name() != name


def test__set_symbol(gov, vault, bunny):
    symbol = vault.name()
    new_symbol = "New Vault symbol"

    with ape.reverts("not allowed"):
        vault.setSymbol(new_symbol, sender=bunny)

    vault.set_role(bunny, ROLES.ALL, sender=gov)

    with ape.reverts("not allowed"):
        vault.setSymbol(new_symbol, sender=bunny)

    assert vault.symbol() != new_symbol

    vault.setSymbol(new_symbol, sender=gov)

    assert vault.symbol() == new_symbol
    assert vault.symbol() != symbol
