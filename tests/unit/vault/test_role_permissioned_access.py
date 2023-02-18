import ape
from utils.constants import ROLES, WEEK
from utils.utils import from_units


def test_set_open_role__by_random_account__reverts(vault, bunny):
    with ape.reverts():
        vault.set_open_role(ROLES.STRATEGY_MANAGER, sender=bunny)


# STRATEGY_MANAGER


def test_add_strategy__set_strategy_role_open__reverts(vault, create_strategy, bunny):
    new_strategy = create_strategy(vault)
    with ape.reverts():
        vault.add_strategy(new_strategy, sender=bunny)


def test_revoke_strategy__set_strategy_role_open__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts():
        vault.revoke_strategy(new_strategy, sender=bunny)


def test_migrate_strategy__set_strategy_role_open__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    other_new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts():
        vault.migrate_strategy(other_new_strategy, new_strategy, sender=bunny)


def test_add_strategy__set_strategy_role_open(vault, create_strategy, bunny, gov):
    new_strategy = create_strategy(vault)
    vault.set_open_role(ROLES.STRATEGY_MANAGER, sender=gov)
    tx = vault.add_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyAdded))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address


def test_revoke_strategy__set_strategy_role_open(vault, create_strategy, bunny, gov):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    vault.set_open_role(ROLES.STRATEGY_MANAGER, sender=gov)
    tx = vault.revoke_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyRevoked))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address


def test_migrate_strategy__set_strategy_role_open(vault, create_strategy, bunny, gov):
    new_strategy = create_strategy(vault)
    other_new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    vault.set_open_role(ROLES.STRATEGY_MANAGER, sender=gov)
    tx = vault.migrate_strategy(other_new_strategy, new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyMigrated))
    assert len(event) == 1
    assert (
        event[0].old_strategy == new_strategy.address
        and event[0].new_strategy == other_new_strategy.address
    )


# ACCOUNTING_MANAGER


def test_process_report__set_accounting_role_open__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts():
        vault.process_report(new_strategy, sender=bunny)


def test_sweep__set_accounting_role_open__reverts(vault, mock_token, bunny):
    with ape.reverts():
        vault.sweep(mock_token, sender=bunny)


def test_update_profit_unlock__accounting_role_closed__reverts(vault, bunny):
    with ape.reverts():
        vault.set_profit_max_unlock_time(WEEK * 2, sender=bunny)


def test_process_report__set_accounting_role_open(
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
    vault.set_open_role(ROLES.ACCOUNTING_MANAGER, sender=gov)
    asset.mint(new_strategy, fish_amount, sender=gov)
    tx = vault.process_report(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address and event[0].gain == fish_amount


def test_sweep__set_accounting_role_open(vault, fish_amount, asset, bunny, gov):
    asset.mint(vault, fish_amount, sender=gov)
    vault.set_open_role(ROLES.ACCOUNTING_MANAGER, sender=gov)
    tx = vault.sweep(asset, sender=bunny)
    event = list(tx.decode_logs(vault.Sweep))
    assert len(event) == 1
    assert event[0].token == asset.address
    assert asset.balanceOf(bunny) == fish_amount


def test_update_profit_unlock__set_accounting_role_open(vault, bunny, gov):
    vault.set_open_role(ROLES.ACCOUNTING_MANAGER, sender=gov)
    tx = vault.set_profit_max_unlock_time(WEEK * 2, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateProfitMaxUnlockTime))
    assert len(event) == 1
    assert event[0].profit_max_unlock_time == WEEK * 2
    vault.profit_max_unlock_time() == WEEK * 2


# DEBT_MANAGER


def test_update_max_debt_for_strategy__set_debt_role_open__reverts(
    vault, create_strategy, bunny, gov
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts():
        vault.update_max_debt_for_strategy(new_strategy, 0, sender=bunny)


def test_update_debt__set_debt_role_open__reverts(vault, create_strategy, bunny, gov):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    with ape.reverts():
        vault.update_debt(new_strategy, 0, sender=bunny)


def test_set_minimum_total_idle__set_debt_role_open__reverts(vault, bunny):
    with ape.reverts():
        vault.set_minimum_total_idle(0, sender=bunny)


def test_set_minimum_total_idle__set_debt_role_open(vault, bunny, gov):
    vault.set_open_role(ROLES.DEBT_MANAGER, sender=gov)
    tx = vault.set_minimum_total_idle(0, sender=bunny)
    event = list(tx.decode_logs(vault.UpdateMinimumTotalIdle))
    assert len(event) == 1
    assert event[0].minimum_total_idle == 0


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


def test_update_max_debt_for_strategy__set_debt_role_open(
    vault, create_strategy, bunny, gov
):
    vault.set_open_role(ROLES.DEBT_MANAGER, sender=gov)
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy, sender=gov)
    tx = vault.update_max_debt_for_strategy(new_strategy, 420, sender=bunny)
    event = list(tx.decode_logs(vault.UpdatedMaxDebtForStrategy))
    assert len(event) == 1
    assert (
        event[0].sender == bunny.address and event[0].strategy == new_strategy.address
    )
    assert event[0].new_debt == 420


# EMERGENCY_MANAGER


def test_shutdown_vault__set__emergency_role_open__reverts(vault, bunny):
    with ape.reverts():
        vault.shutdown_vault(sender=bunny)


def test_shutdown_vault__set__emergency_role_open(vault, bunny, gov):
    with ape.reverts():
        vault.shutdown_vault(sender=bunny)
    vault.set_open_role(ROLES.EMERGENCY_MANAGER, sender=gov)
    tx = vault.shutdown_vault(sender=bunny)
    event = list(tx.decode_logs(vault.Shutdown))
    assert len(event) == 1
