import ape
import pytest
from ape import chain
from utils import checks
from utils.utils import sleep
from utils.constants import ROLES, ZERO_ADDRESS, DAY, StrategyChangeType


def test_add_strategy__with_valid_strategy(chain, gov, vault, create_strategy):
    new_strategy = create_strategy(vault)

    snapshot = chain.pending_timestamp
    tx = vault.add_strategy(new_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyChanged))

    assert len(event) == 1
    assert event[0].strategy == new_strategy.address
    assert event[0].change_type == StrategyChangeType.ADDED

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


def test_add_strategy__with_generic_strategy(
    gov, vault, asset, create_generic_strategy
):
    # create strategy with no vault but same asset
    strategy = create_generic_strategy(asset)

    snapshot = chain.pending_timestamp
    tx = vault.add_strategy(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyChanged))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].change_type == StrategyChangeType.ADDED

    strategy_params = vault.strategies(strategy)
    assert strategy_params.activation == pytest.approx(snapshot, abs=1)
    assert strategy_params.current_debt == 0
    assert strategy_params.max_debt == 0
    assert strategy_params.last_report == pytest.approx(snapshot, abs=1)


def test_revoke_strategy__with_existing_strategy(gov, vault, strategy):
    tx = vault.revoke_strategy(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyChanged))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED

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


def test_force_revoke_strategy__with_existing_strategy(gov, vault, strategy):
    tx = vault.force_revoke_strategy(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyChanged))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED

    strategy_params = vault.strategies(strategy)
    checks.check_revoked_strategy(strategy_params)


def test_force_revoke_strategy__with_non_zero_debt(
    gov, asset, vault, strategy, mint_and_deposit_into_vault, add_debt_to_strategy
):
    mint_and_deposit_into_vault(vault)
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance

    add_debt_to_strategy(gov, strategy, vault, new_debt)

    tx = vault.force_revoke_strategy(strategy.address, sender=gov)

    # strategy report error
    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == 0
    assert event[0].loss == new_debt
    assert event[0].current_debt == 0
    assert event[0].total_fees == 0
    assert event[0].total_refunds == 0

    # strategy changed event
    event = list(tx.decode_logs(vault.StrategyChanged))
    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].change_type == StrategyChangeType.REVOKED

    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 0

    strategy_params = vault.strategies(strategy)
    checks.check_revoked_strategy(strategy_params)


def test_force_revoke_strategy__with_inactive_strategy__fails_with_error(
    gov, vault, create_strategy
):
    strategy = create_strategy(vault)

    with ape.reverts("strategy not active"):
        vault.force_revoke_strategy(strategy.address, sender=gov)
