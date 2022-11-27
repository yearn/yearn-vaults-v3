from ape import chain
import pytest
from utils.constants import ROLES
from utils.utils import days_to_secs

def test__report_with_protocol_fees(
    vault_factory,
    create_vault,
    asset,
    fish_amount,
    create_strategy,
    user_deposit,
    fish,
    add_strategy_to_vault,
    add_debt_to_strategy,
    gov,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10

    vault_factory.set_protocol_fee_bps(25, sender=gov)
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    assert vault.price_per_share() == int(10 ** 18)
    days_passed = 365
    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = vault.last_report() + days_to_secs(days_passed)
    tx = vault.process_report(strategy, sender=gov)

    assert vault.balanceOf(gov.address) == amount * 0.0025 * days_passed / 365
    assert pytest.approx(vault.price_per_share(), rel=1e-5) == int(10 ** 18) * (1 - 0.0025 * days_passed / 365)

