from utils.utils import days_to_secs
from utils.constants import MAX_BPS, WEEK, YEAR, DAY
from ape import chain, reverts
import pytest


def test_total_debt(
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

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    initial_timestamp = chain.pending_timestamp

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # There are no profits, so method should return value without estimation
    assert strategy.totalAssets() == amount
    assert vault.total_debt() == amount

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert vault.totalAssets() == amount + first_profit
    assert vault.total_debt() == amount + first_profit
    post_profit_totalSupply = vault.totalSupply()

    assert post_profit_totalSupply > amount

    # We increase time and check estimation
    chain.pending_timestamp = initial_timestamp + days_to_secs(4)
    chain.mine(timestamp=chain.pending_timestamp)

    assert post_profit_totalSupply > vault.totalSupply()
    assert pytest.approx(
        vault.totalSupply(), rel=1e-5
    ) == post_profit_totalSupply - first_profit * days_to_secs(4) / days_to_secs(14)

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == vault.total_debt()
    assert vault.total_debt() == amount + first_profit
    assert pytest.approx(vault.totalSupply(), rel=1e-5) == amount
