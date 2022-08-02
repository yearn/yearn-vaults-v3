from utils.utils import days_to_secs
from utils.constants import MAX_BPS
from ape import chain, reverts
import pytest


def test_totalDebt(
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
    Method vault.totalDebt() returns the total debt that the vault has. If there are profits that have been unlocked,
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
    assert vault.totalDebt() == amount

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert vault.totalAssets() == amount
    assert vault.totalDebt() == amount

    # We increase time and check estimation
    chain.pending_timestamp = days_to_secs(4)
    chain.mine(timestamp=chain.pending_timestamp)

    # There are profits, and values are not updated. We need to estimate
    assert vault.totalAssets() == vault.totalDebt()
    assert vault.totalDebt() == pytest.approx(
        amount + first_profit / vault.profit_max_unlock_time() * days_to_secs(4),
        rel=1e-4,
    )

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)
    assert vault.totalAssets() == vault.totalDebt()
    assert vault.totalDebt() == pytest.approx(amount + first_profit, rel=1e-5)


def test_profitDistributionRate(
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
    assert vault.totalDebt() == amount

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert vault.profitDistributionRate() == int(
        first_profit / days_to_secs(7) * MAX_BPS
    )

    # We increase time and check estimation
    chain.pending_timestamp = days_to_secs(4)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.profitDistributionRate() == int(
        first_profit / days_to_secs(7) * MAX_BPS
    )

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.profit_end_date() < days_to_secs(10)
    assert vault.profitDistributionRate() == 0


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

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.totalDebt() == amount
    assert vault.total_idle() == 0
    assert vault.profit_max_unlock_time() == days_to_secs(7)
    assert vault.profitDistributionRate() == 0

    # We call process_report at t_1 (days)
    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    assert vault.totalAssets() == amount
    assert vault.totalDebt() == amount
    assert vault.total_idle() == 0

    assert vault.profitDistributionRate() == int(
        first_profit / vault.profit_max_unlock_time() * MAX_BPS
    )
    assert vault.profit_last_update() == pytest.approx(chain.pending_timestamp, abs=5)

    # We move in time and we keep checking values
    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == pytest.approx(
        amount + first_profit / vault.profit_max_unlock_time() * days_to_secs(2),
        1e-5,
    )

    chain.pending_timestamp = days_to_secs(8) + 15
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == pytest.approx(amount + first_profit, 1e-5)

    vault.update_profit_distribution(sender=gov)

    assert vault.totalAssets() == pytest.approx(amount + first_profit, 1e-5)
    assert vault.totalDebt() == pytest.approx(amount + first_profit, 1e-5)
    assert vault.profitDistributionRate() == 0
    assert vault.profit_last_update() == pytest.approx(chain.pending_timestamp, abs=5)


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
    assert vault.totalDebt() == amount
    assert vault.total_idle() == 0

    assert vault.profitDistributionRate() == 0
    assert vault.profit_max_unlock_time() == days_to_secs(7)

    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    assert vault.totalAssets() == amount
    assert vault.totalDebt() == amount
    assert vault.total_idle() == 0

    assert vault.profitDistributionRate() == int(
        first_profit / days_to_secs(7) * MAX_BPS
    )
    dist_rate_before_second_profit = vault.profitDistributionRate()
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
    assert event[0].total_gain == first_profit + second_profit

    assert vault.totalAssets() == pytest.approx(
        amount + first_profit / days_to_secs(7) * days_to_secs(2), 1e-5
    )
    # New distribution rate should be higher than the one before, but smaller than both distribution rates summed
    # together as we are applying a proportional average
    assert vault.profitDistributionRate() > dist_rate_before_second_profit
    assert (
        vault.profitDistributionRate()
        < dist_rate_before_second_profit + second_profit / days_to_secs(7) * MAX_BPS
    )

    # Same as before applies on profit_end_date
    assert vault.profit_end_date() > profit_end_date_before_second_profit
    assert vault.profit_end_date() < days_to_secs(3) + vault.profit_max_unlock_time()

    chain.pending_timestamp = days_to_secs(10) + 15
    chain.mine(timestamp=chain.pending_timestamp)

    vault.update_profit_distribution(sender=gov)

    assert vault.totalAssets() == pytest.approx(
        amount + first_profit + second_profit, 1e-5
    )
    assert vault.profitDistributionRate() == 0


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

    assert vault.profitDistributionRate() == int(profit / days_to_secs(7) * MAX_BPS)
    dist_rate_profit_1_before_loss = vault.profitDistributionRate()

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].loss == loss
    assert event[0].total_loss == loss
    assert event[0].total_gain == profit

    assert vault.profitDistributionRate() < dist_rate_profit_1_before_loss

    chain.pending_timestamp = days_to_secs(10) + 15
    chain.mine(timestamp=chain.pending_timestamp)

    vault.update_profit_distribution(sender=gov)

    assert vault.totalAssets() == pytest.approx(amount + profit - loss, 1e-5)
    assert vault.profitDistributionRate() / MAX_BPS == 0


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
    Loss is too big for the profitBuffer, so it should drain it and reset profitDistributionRate
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
    assert event[0].total_gain == first_profit
    assert event[0].total_loss == big_loss

    # There should not be any profit on the history
    assert vault.profitDistributionRate() == 0
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
    # set up fee manager and fees
    management_fee = 0
    performance_fee = 1000
    set_fees_for_strategy(gov, strategy, fee_manager, management_fee, performance_fee)

    assert strategy.totalAssets() == amount

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.totalDebt() == amount
    assert vault.total_idle() == 0

    assert vault.profitDistributionRate() == 0
    assert vault.profit_max_unlock_time() == days_to_secs(7)

    # We call process_report at t_1
    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    assert vault.totalAssets() == amount
    assert vault.totalDebt() == amount
    assert vault.total_idle() == 0

    profit_without_fees = first_profit * (MAX_BPS - performance_fee) / MAX_BPS
    assert vault.profitDistributionRate() / MAX_BPS == pytest.approx(
        profit_without_fees / days_to_secs(7), 1e-5
    )
    assert vault.profit_last_update() == pytest.approx(chain.pending_timestamp, abs=5)


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
    assert vault.totalDebt() == amount
    assert vault.total_idle() == 0

    assert vault.profitDistributionRate() == 0
    assert vault.profit_max_unlock_time() == days_to_secs(7)

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
    last_update_before_deposit = vault.profit_last_update()

    vault.deposit(deposit, fish, sender=fish)

    # During the deposit, profit locking values have been updated
    assert last_update_before_deposit < vault.profit_last_update()
    assert balance_before_deposit < vault.balanceOf(fish)
    assert pps_before_deposit < vault.price_per_share()

    # Due to the report of profits, vault pps should be higher: for the same amount, second deposit gives fewer shares
    assert balance_before_deposit > (vault.balanceOf(fish) - balance_before_deposit)

    # We move in time and we keep checking values
    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    balance_before_withdraw = vault.balanceOf(fish)
    last_update_before_withdraw = vault.profit_last_update()
    pps_before_withdraw = vault.price_per_share()

    vault.withdraw(deposit, fish, fish, [strategy], sender=fish)

    # During the withdrawal, profit locking values have been updated
    assert last_update_before_withdraw < vault.profit_last_update()
    assert balance_before_withdraw > vault.balanceOf(fish)
    # pps keeps increasing as profits are being released
    assert pps_before_withdraw < vault.price_per_share()


def test_set_unlocking_time_higher_value(
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

    vault = create_vault(asset)
    strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We change locking time and create a virtual profit
    new_unlocking_time = days_to_secs(10)
    vault.set_profit_max_unlock_time(new_unlocking_time, sender=gov)

    asset.transfer(strategy, profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert vault.profit_max_unlock_time() == days_to_secs(10)
    assert vault.profitDistributionRate() == int(profit / days_to_secs(10) * MAX_BPS)


def test_set_unlocking_time_lower_value(
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

    vault = create_vault(asset)
    strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We change locking time and create a virtual profit
    new_unlocking_time = days_to_secs(6)
    vault.set_profit_max_unlock_time(new_unlocking_time, sender=gov)

    asset.transfer(strategy, profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert vault.profit_max_unlock_time() == days_to_secs(6)
    assert vault.profitDistributionRate() == int(profit / days_to_secs(6) * MAX_BPS)
