import ape
from utils.constants import ROLES
from utils.utils import days_to_secs


# STRATEGY_MANAGER


def test_add_strategy__no_strategy_manager__reverts(vault, create_strategy, bunny):
    new_strategy = create_strategy(vault)
    with ape.reverts():
        vault.add_strategy(new_strategy, sender=bunny)


def test_add_strategy__strategy_manager(vault, create_strategy, gov, bunny):
    # We temporarily give bunny the role of STRATEGY_MANAGER
    vault.set_role(bunny.address, ROLES.STRATEGY_MANAGER, sender=gov)

    new_strategy = create_strategy(vault)
    tx = vault.add_strategy(new_strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyAdded))
    assert len(event) == 1
    assert event[0].strategy == new_strategy.address


def test_revoke_strategy__no_strategy_manager__reverts(vault, strategy, bunny):
    with ape.reverts():
        vault.revoke_strategy(strategy, sender=bunny)


def test_revoke_strategy__strategy_manager(vault, strategy, gov, bunny):
    # We temporarily give bunny the role of STRATEGY_MANAGER
    vault.set_role(bunny.address, ROLES.STRATEGY_MANAGER, sender=gov)

    tx = vault.revoke_strategy(strategy, sender=bunny)
    event = list(tx.decode_logs(vault.StrategyRevoked))
    assert len(event) == 1
    assert event[0].strategy == strategy.address


def test_migrate_strategy__no_strategy_manager__reverts(
    vault, strategy, create_strategy, bunny
):
    new_strategy = create_strategy(vault)
    with ape.reverts():
        vault.migrate_strategy(strategy, new_strategy, sender=bunny)


def test_migrate_strategy__strategy_manager(
    vault, strategy, create_strategy, gov, bunny
):
    # We temporarily give bunny the role of STRATEGY_MANAGER
    vault.set_role(bunny.address, ROLES.STRATEGY_MANAGER, sender=gov)

    new_strategy = create_strategy(vault)

    tx = vault.migrate_strategy(new_strategy, strategy, sender=bunny)

    event = list(tx.decode_logs(vault.StrategyRevoked))
    assert len(event) == 1
    assert event[0].strategy == strategy.address

    event = list(tx.decode_logs(vault.StrategyMigrated))
    assert len(event) == 1
    assert event[0].old_strategy == strategy.address
    assert event[0].new_strategy == new_strategy.address


# DEBT_MANAGER


def test_set_minimum_total_idle__no_debt_manager__reverts(bunny, vault):
    minimum_total_idle = 1
    with ape.reverts():
        vault.set_minimum_total_idle(minimum_total_idle, sender=bunny)


def test_set_minimum_total_idle__debt_manager(gov, vault, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_role(bunny.address, ROLES.DEBT_MANAGER, sender=gov)

    assert vault.minimum_total_idle() == 0
    minimum_total_idle = 1
    vault.set_minimum_total_idle(minimum_total_idle, sender=bunny)
    assert vault.minimum_total_idle() == 1


def test_update_max_debt__no_debt_manager__reverts(vault, strategy, bunny):
    assert vault.strategies(strategy).max_debt == 0
    max_debt_for_strategy = 1
    with ape.reverts():
        vault.update_max_debt_for_strategy(
            strategy, max_debt_for_strategy, sender=bunny
        )


def test_update_max_debt__debt_manager(gov, vault, strategy, bunny):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_role(bunny.address, ROLES.DEBT_MANAGER, sender=gov)

    assert vault.strategies(strategy).max_debt == 0
    max_debt_for_strategy = 1
    vault.update_max_debt_for_strategy(strategy, max_debt_for_strategy, sender=bunny)
    assert vault.strategies(strategy).max_debt == 1


def test_update_debt__no_debt_manager__reverts(vault, strategy, bunny):
    with ape.reverts():
        vault.update_debt(strategy, sender=bunny)


def test_update_debt__debt_manager(
    gov, mint_and_deposit_into_vault, vault, strategy, bunny
):
    # We temporarily give bunny the role of DEBT_MANAGER
    vault.set_role(bunny.address, ROLES.DEBT_MANAGER, sender=gov)

    # Provide vault with funds
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)

    max_debt_for_strategy = 1
    vault.update_max_debt_for_strategy(strategy, max_debt_for_strategy, sender=bunny)

    tx = vault.update_debt(strategy, sender=bunny)

    event = list(tx.decode_logs(vault.DebtUpdated))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].current_debt == 0
    assert event[0].new_debt == 1


# EMERGENCY_MANAGER


def test_shutdown_vault__no_emergency_manager__reverts(vault, bunny):
    with ape.reverts():
        vault.shutdown_vault(sender=bunny)


def test_shutdown_vault__emergency_manager(gov, vault, bunny):
    # We temporarily give bunny the role of EMERGENCY_MANAGER
    vault.set_role(bunny.address, ROLES.EMERGENCY_MANAGER, sender=gov)

    assert vault.shutdown() == False
    tx = vault.shutdown_vault(sender=bunny)

    assert vault.shutdown() == True
    event = list(tx.decode_logs(vault.Shutdown))
    assert len(event) == 1
    # lets ensure that we give the EMERGENCY_MANAGER DEBT_MANAGER permissions after shutdown
    # EMERGENCY_MANAGER=4 DEBT_MANGER=2 -> binary or operation should give us 6 (110)
    assert vault.roles(bunny) == 6


# ACCOUNTING_MANAGER


def test_process_report__no_accounting_manager__reverts(vault, strategy, bunny):
    with ape.reverts():
        vault.process_report(strategy, sender=bunny)


def test_process_report__accounting_manager(
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
    vault.set_role(bunny.address, ROLES.ACCOUNTING_MANAGER, sender=gov)

    # Provide liquidity into vault
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)
    # add debt to strategy
    add_debt_to_strategy(gov, strategy, vault, 2)
    # airdrop gain to strategy
    airdrop_asset(gov, asset, strategy, 1)

    tx = vault.process_report(strategy.address, sender=bunny)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == 1
    assert event[0].loss == 0


def test_sweep__no_accounting_manager__reverts(vault, strategy, bunny):
    with ape.reverts():
        vault.process_report(strategy, sender=bunny)


def test_sweep__accounting_manager(
    gov,
    asset,
    vault,
    bunny,
    airdrop_asset,
    mint_and_deposit_into_vault,
):
    # We temporarily give bunny the role of ACCOUNTING_MANAGER
    vault.set_role(bunny.address, ROLES.ACCOUNTING_MANAGER, sender=gov)

    vault_balance = 10**22
    asset_airdrop = vault_balance // 10
    mint_and_deposit_into_vault(vault, gov, vault_balance)

    airdrop_asset(gov, asset, vault, asset_airdrop)

    tx = vault.sweep(asset.address, sender=bunny)
    event = list(tx.decode_logs(vault.Sweep))

    assert len(event) == 1
    assert event[0].token == asset.address
    assert event[0].amount == asset_airdrop
