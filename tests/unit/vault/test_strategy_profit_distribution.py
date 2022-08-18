from utils.utils import days_to_secs
from utils.constants import MAX_BPS, WEEK
from ape import chain, reverts
import pytest


def test_total_debt(
    create_vault,
    asset,
    create_strategy,
    user_deposit,
    fish,
    add_strategy_to_vault,
    add_debt_to_strategy,
    gov,
):
    """
    Method vault.total_debt() returns the total debt that the vault has. If there are profits that have been unlocked,
    it will estimate them.
    """

    amount = 10**9
    first_profit = 10**9

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

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

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount

    # We increase time and check estimation
    chain.pending_timestamp = days_to_secs(4)
    chain.mine(timestamp=chain.pending_timestamp)

    # There are profits, and values are not updated. We need to estimate
    assert vault.totalAssets() == vault.total_debt()
    assert vault.total_debt() == pytest.approx(
        amount + first_profit / WEEK * days_to_secs(4),
        rel=1e-4,
    )

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)
    assert vault.totalAssets() == vault.total_debt()
    assert vault.total_debt() == pytest.approx(amount + first_profit, rel=1e-5)


def test_profit_distribution_rate(
    create_vault,
    asset,
    create_strategy,
    user_deposit,
    fish,
    add_strategy_to_vault,
    add_debt_to_strategy,
    gov,
):
    amount = 10**9
    first_profit = 10**9

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

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

    assert vault.profit_distribution_rate() == int(first_profit / WEEK * MAX_BPS)

    # We increase time and check estimation
    chain.pending_timestamp = days_to_secs(4)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.profit_distribution_rate() == int(first_profit / WEEK * MAX_BPS)

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.profit_end_date() < days_to_secs(10)
    assert vault.profit_distribution_rate() == 0


def test_profit_distribution__one_gain(
    gov,
    fish,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    By day 8, total_assets should be 1000 + 1000 = 2000 assets
    """

    amount = 10**9
    first_profit = 10**9

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    assert strategy.totalAssets() == amount

    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0
    pps_before_profit = vault.price_per_share()

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0

    assert vault.profit_distribution_rate() == 0

    # We call process_report at t_1 (days)
    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0
    assert vault.price_per_share() == pps_before_profit

    assert vault.profit_distribution_rate() == int(first_profit / WEEK * MAX_BPS)
    assert vault.profit_last_update() == pytest.approx(chain.pending_timestamp, abs=5)

    # We move in time and we keep checking values
    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == pytest.approx(
        amount + first_profit / WEEK * days_to_secs(2),
        1e-5,
    )

    chain.pending_timestamp = days_to_secs(8) + 15
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == pytest.approx(amount + first_profit, 1e-5)
    assert vault.total_debt() == pytest.approx(amount + first_profit, 1e-5)
    assert vault.profit_distribution_rate() == 0


def test_profit_distribution__two_gain(
    gov,
    fish,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets and a gain on day 3 of 500 assets.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    By day 8, total_assets should be 1000 + 1000 + 500 = 2500 assets
    """

    amount = 10**9
    first_profit = 10**9
    second_profit = 10**9

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0

    assert vault.profit_distribution_rate() == 0

    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0

    assert vault.profit_distribution_rate() == int(first_profit / WEEK * MAX_BPS)
    dist_rate_before_second_profit = vault.profit_distribution_rate()
    assert vault.profit_end_date() == pytest.approx(days_to_secs(8), abs=5)
    profit_end_date_before_second_profit = vault.profit_end_date()

    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    # We create second virtual profit
    asset.transfer(strategy, second_profit, sender=fish)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == second_profit

    assert vault.totalAssets() == pytest.approx(
        amount + first_profit / WEEK * days_to_secs(2), 1e-5
    )

    # New distribution rate should be higher than the one before, but smaller than both distribution rates summed
    # together as we are applying a proportional average
    assert vault.profit_distribution_rate() > dist_rate_before_second_profit
    assert (
        vault.profit_distribution_rate()
        < dist_rate_before_second_profit + second_profit / WEEK * MAX_BPS
    )

    # Same as before applies on profit_end_date
    assert vault.profit_end_date() > profit_end_date_before_second_profit
    assert vault.profit_end_date() < days_to_secs(3) + WEEK

    chain.pending_timestamp = days_to_secs(10) + 15
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == pytest.approx(
        amount + first_profit + second_profit, 1e-5
    )
    assert vault.profit_distribution_rate() == 0


def test_profit_distribution__one_gain_one_loss(
    gov,
    fish,
    asset,
    create_vault,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets and a loss on
    day 4 of 500 assets.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    By day 8, total_assets should be 1000 + 1000 - 500 = 1500 assets
    """

    amount = 10**9
    profit = 10**9
    loss = int(10**9 / 2)

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=days_to_secs(1))

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == profit

    assert strategy.totalAssets() == amount + profit

    chain.pending_timestamp = days_to_secs(4)
    chain.mine(timestamp=chain.pending_timestamp)

    strategy.setLoss(fish, loss, sender=gov)
    assert strategy.totalAssets() == amount + profit - loss

    assert vault.profit_distribution_rate() == int(profit / WEEK * MAX_BPS)
    dist_rate_profit_1_before_loss = vault.profit_distribution_rate()

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].loss == loss

    assert vault.profit_distribution_rate() < dist_rate_profit_1_before_loss

    chain.pending_timestamp = days_to_secs(10) + 15
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == pytest.approx(amount + profit - loss, 1e-5)
    assert vault.profit_distribution_rate() / MAX_BPS == 0


def test_profit_distribution__one_gain_one_big_loss(
    gov,
    fish,
    asset,
    create_vault,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    """
    Scenario where there is a gain on day 1 of 500 assets, and a loss on
    day 2 of 1000 assets.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    By day 2, total_assets should be 1000 + 500 - 1000 = 500 assets.
    Loss is too big for the profitBuffer, so it should drain it and reset profit_distribution_rate
    """

    amount = 10**9
    first_profit = int(10**9 / 2)
    big_loss = 10**9

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)

    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=days_to_secs(1))

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    chain.pending_timestamp = days_to_secs(2)
    chain.mine(timestamp=days_to_secs(2))

    strategy.setLoss(fish, big_loss, sender=gov)
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].loss == big_loss

    # There should not be any profit on the history
    assert vault.profit_distribution_rate() == 0
    assert vault.totalAssets() == pytest.approx(10**9 / 2, 1e-5)


def test_profit_distribution__one_gain_with_fees(
    gov,
    fish,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    set_fees_for_strategy,
    fee_manager,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets and there are performance fees.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    """

    amount = 10**9
    profit = 10**9

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    # set up fee manager and fees
    management_fee = 0
    performance_fee = 1_000
    set_fees_for_strategy(gov, strategy, fee_manager, management_fee, performance_fee)

    assert strategy.totalAssets() == amount

    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0
    pps_before_profit = vault.price_per_share()

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    assert vault.profit_distribution_rate() == 0

    # We call process_report at t_1
    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == profit

    assert vault.totalAssets() == amount + profit * performance_fee / MAX_BPS
    assert vault.total_debt() == amount + profit * performance_fee / MAX_BPS
    assert vault.total_idle() == 0

    assert vault.price_per_share() == pps_before_profit
    assert vault.balanceOf(fee_manager) == vault.convertToShares(
        int(profit * performance_fee / MAX_BPS)
    )

    profit_without_fees = profit * (MAX_BPS - performance_fee) / MAX_BPS
    assert vault.profit_distribution_rate() / MAX_BPS == pytest.approx(
        profit_without_fees / WEEK, 1e-5
    )


def test_profit_distribution__one_gain_with_100_percent_fees(
    gov,
    fish,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    set_fees_for_strategy,
    flexible_fee_manager,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets and there are performance fees of 100% of profit.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    """

    amount = 10**9
    profit = 10**9

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset, fee_manager=flexible_fee_manager)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    # set up fee manager and fees
    management_fee = 0
    performance_fee = 10_000
    set_fees_for_strategy(
        gov, strategy, flexible_fee_manager, management_fee, performance_fee
    )

    assert strategy.totalAssets() == amount

    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0
    pps_before_profit = vault.price_per_share()

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    assert vault.profit_distribution_rate() == 0

    # We call process_report at t_1
    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == profit

    assert vault.totalAssets() == amount + profit
    assert vault.total_debt() == amount + profit
    assert vault.total_idle() == 0

    assert vault.price_per_share() == pps_before_profit
    assert vault.balanceOf(flexible_fee_manager) == vault.convertToShares(profit)
    assert vault.profit_distribution_rate() == 0


def test_profit_distribution__one_gain_with_200_percent_fees(
    gov,
    fish,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    set_fees_for_strategy,
    flexible_fee_manager,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets and there are performance fees of 200% of profit.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    """

    amount = 10**9
    profit = 10**9

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset, fee_manager=flexible_fee_manager)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    # set up fee manager and fees
    management_fee = 0
    performance_fee = 20_000
    set_fees_for_strategy(
        gov, strategy, flexible_fee_manager, management_fee, performance_fee
    )

    assert strategy.totalAssets() == amount

    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0
    pps_before_profit = vault.price_per_share()

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    assert vault.profit_distribution_rate() == 0

    # We call process_report at t_1
    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == profit

    assert vault.totalAssets() == amount + profit
    assert vault.total_debt() == amount + profit
    assert vault.total_idle() == 0

    # Due to the fact that we were unable to pay fees with profit, pps its lowered
    assert vault.price_per_share() < pps_before_profit
    # Fee Managers gets shares at 1:1 price
    assert vault.balanceOf(flexible_fee_manager) == int(2 * profit)
    assert vault.profit_distribution_rate() == 0


def test_profit_distribution__one_gain_with_200_percent_fees_and_enough_pending_profit(
    gov,
    fish,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    set_fees_for_strategy,
    flexible_fee_manager,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets without fees. After there is another profit
    and there are performance fees of 200% of profit.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    """

    amount = 10**9
    first_profit = int(5 * 10**9)
    second_profit = int(10**9)

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset, fee_manager=flexible_fee_manager)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    assert strategy.totalAssets() == amount

    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    assert vault.profit_distribution_rate() == 0

    # We call process_report at t_1
    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    # set up fee manager and fees
    management_fee = 0
    performance_fee = 20_000
    set_fees_for_strategy(
        gov, strategy, flexible_fee_manager, management_fee, performance_fee
    )

    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    dist_rate_before_fees = vault.profit_distribution_rate()
    pps_before_fees = vault.price_per_share()

    # We create a virtual profit
    asset.transfer(strategy, second_profit, sender=fish)
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == second_profit

    # Due to the fact that we were able to pay fees with profit, pps remains
    assert vault.price_per_share() == pytest.approx(pps_before_fees, 1e-5)
    # Fee Managers gets shares at pps price without affecting it
    assert vault.balanceOf(flexible_fee_manager) == int(
        vault.convertToShares(second_profit * 2)
    )
    # dist rate gets lowered, but there are still profits being distributed
    assert vault.profit_distribution_rate() < dist_rate_before_fees


def test_profit_distribution__one_gain_one_deposit_one_withdraw(
    gov,
    fish,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets, a deposit on day 2 of 1000 assets and a withdrawal
    of 1000 assets on day 3.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    """

    amount = 10**9
    first_profit = 10**9
    deposit = 10**9
    withdraw = deposit

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    assert strategy.totalAssets() == amount

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0

    assert vault.profit_distribution_rate() == 0

    # We call process_report at t_1
    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    vault.process_report(strategy, sender=gov)

    # We move in time and we keep checking values
    chain.pending_timestamp = days_to_secs(2)
    chain.mine(timestamp=chain.pending_timestamp)

    # pps should be higher than 1 (already some profits have been unlocked), but lower
    # than 2 (not all profits have been unlocked)
    assert 1 < vault.price_per_share() / 10 ** vault.decimals() < 2
    assert vault.balanceOf(fish) == amount

    pps_before_deposit = vault.price_per_share()
    balance_before_deposit = vault.balanceOf(fish)

    vault.deposit(deposit, fish, sender=fish)

    assert balance_before_deposit < vault.balanceOf(fish)
    assert pps_before_deposit < vault.price_per_share()

    # Due to the report of profits, vault pps should be higher: for the same amount, second deposit gives fewer shares
    assert balance_before_deposit > (vault.balanceOf(fish) - balance_before_deposit)

    # We move in time and we keep checking values
    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    balance_before_withdraw = vault.balanceOf(fish)
    pps_before_withdraw = vault.price_per_share()

    vault.withdraw(deposit, fish, fish, [strategy], sender=fish)

    assert balance_before_withdraw > vault.balanceOf(fish)
    # pps keeps increasing as profits are being released
    assert pps_before_withdraw < vault.price_per_share()


def test_unlocking_time_to_zero_days(
    gov,
    fish,
    asset,
    create_vault,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
):
    amount = 10**9
    profit = 10**9

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset, max_profit_locking_time=0)
    strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    asset.transfer(strategy, profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.profit_distribution_rate() == 0
    assert vault.totalAssets() == pytest.approx(amount + profit, 1e-6)
