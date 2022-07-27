from utils.utils import days_to_secs
from utils.constants import MAX_BPS
from ape import chain, reverts
from ape.exceptions import ContractLogicError
import pytest


def test_totalAssets(
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
    Method vault.totalAssets() returns all assets that the vault has. If there are profits locked, it will
    estimate them.
    Test wants to check that we are able to estimate them properly.
    """

    amount = 10**9
    first_profit = 10**9
    second_profit = int(10**9 / 2)

    # We reset time to 1 to facilitate reporting
    chain.pending_timestamp = 1
    chain.mine(timestamp=chain.pending_timestamp)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    assert strategy.totalAssets() == amount
    assert vault.profit_buffer() == 0

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert vault.totalAssets() == amount
    assert vault.totalDebt() == amount

    # We increase time and check estimation
    chain.pending_timestamp = days_to_secs(4)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == vault.totalDebt()
    assert vault.totalDebt() == pytest.approx(
        amount + first_profit / vault.profit_unlock_time() * days_to_secs(4), rel=1e-4
    )

    # We create a second virtual profit
    chain.pending_timestamp = days_to_secs(5)
    chain.mine(timestamp=chain.pending_timestamp)

    asset.transfer(strategy, second_profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    # Some of the first profit but second profit has not yet been unlocked
    assert vault.totalDebt() == pytest.approx(
        amount + first_profit / vault.profit_unlock_time() * days_to_secs(5), rel=1e-4
    )

    chain.pending_timestamp = days_to_secs(6)
    chain.mine(timestamp=chain.pending_timestamp)

    # Some of the first profit and some of the  second profit
    assert vault.totalDebt() == pytest.approx(
        amount
        + first_profit / vault.profit_unlock_time() * days_to_secs(6)
        + second_profit / vault.profit_unlock_time() * days_to_secs(1),
        rel=1e-4,
    )

    chain.pending_timestamp = days_to_secs(9)
    chain.mine(timestamp=chain.pending_timestamp)
    # Only second profit as first profit has already been unlocked
    assert vault.totalDebt() == pytest.approx(
        amount
        + first_profit
        + second_profit / vault.profit_unlock_time() * days_to_secs(4),
        rel=1e-4,
    )


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

    assert vault.profit_buffer() == 0
    assert vault.profit_unlock_time() == days_to_secs(7)

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

    assert vault.profit_buffer() == first_profit
    assert vault.profit_history(0).distribution_rate / MAX_BPS == pytest.approx(
        first_profit / int(vault.profit_unlock_time()), 1e-5
    )
    assert days_to_secs(1) <= vault.last_profit_buffer_update() < days_to_secs(1) + 15

    # We move in time and we keep checking values
    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == pytest.approx(
        amount + vault.profit_history(0).distribution_rate * days_to_secs(2) / MAX_BPS,
        1e-5,
    )

    # We update profit values manually to current time
    vault.update_profit_buffer(sender=gov)

    assert vault.profit_buffer() == pytest.approx(
        first_profit
        - vault.profit_history(0).distribution_rate * days_to_secs(2) / MAX_BPS,
        1e-5,
    )
    assert vault.profit_history(0).distribution_rate / MAX_BPS == pytest.approx(
        first_profit / (vault.profit_unlock_time()), 1e-5
    )

    chain.pending_timestamp = days_to_secs(8)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == pytest.approx(amount + first_profit, 1e-5)

    vault.update_profit_buffer(sender=gov)

    assert vault.totalAssets() == pytest.approx(amount + first_profit, 1e-5)
    assert vault.totalDebt() == pytest.approx(amount + first_profit, 1e-5)
    assert vault.profit_buffer() / 10 ** vault.decimals() == pytest.approx(0, abs=0.5)
    with reverts():
        vault.profit_history(0)


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
    By day 10, total_assets should be 1000 + 1000 + 500 = 2500 assets
    """

    amount = 10**9
    first_profit = 10**9
    second_profit = int(10**9 / 2)

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

    assert vault.profit_buffer() == 0
    assert vault.profit_unlock_time() == days_to_secs(7)

    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    assert vault.totalAssets() == amount
    assert vault.totalDebt() == amount
    assert vault.total_idle() == 0

    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    asset.transfer(strategy, second_profit, sender=fish)

    assert vault.totalAssets() == pytest.approx(
        amount + vault.profit_history(0).distribution_rate * days_to_secs(2) / MAX_BPS,
        1e-5,
    )

    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == second_profit
    assert event[0].total_gain == first_profit + second_profit

    assert vault.totalAssets() == pytest.approx(
        amount + vault.profit_history(0).distribution_rate * days_to_secs(2) / MAX_BPS,
        1e-5,
    )
    assert vault.totalDebt() == pytest.approx(
        amount + vault.profit_history(0).distribution_rate * days_to_secs(2) / MAX_BPS,
        1e-5,
    )

    chain.pending_timestamp = days_to_secs(8) + 15
    chain.mine(timestamp=chain.pending_timestamp)

    vault.update_profit_buffer(sender=gov)

    # First profit should be gone already, therefore we should only have second profit on history
    assert vault.profit_history(0).distribution_rate / MAX_BPS == pytest.approx(
        second_profit / vault.profit_unlock_time(), 1e-5
    )

    chain.pending_timestamp = days_to_secs(10) + 15
    chain.mine(timestamp=chain.pending_timestamp)

    vault.update_profit_buffer(sender=gov)

    # All profits should have been unlocked
    with reverts():
        vault.profit_history(0)

    assert vault.totalAssets() == pytest.approx(
        amount + first_profit + second_profit, 1e-5
    )
    assert vault.profit_buffer() / 10 ** vault.decimals() == pytest.approx(0, abs=0.5)


def test_profit_distribution__two_gain_one_loss(
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
    Scenario where there is a gain on day 1 of 1000 assets, a gain on day 3 of 500 assets and a loss on
    day 4 of 500 assets.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    By day 10, total_assets should be 1000 + 1000 + 500 - 500 = 2000 assets
    """

    amount = 10**9
    first_profit = 10**9
    second_profit = int(10**9 / 2)
    first_loss = second_profit

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

    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=days_to_secs(3))

    asset.transfer(strategy, second_profit, sender=fish)

    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == second_profit
    assert event[0].total_gain == first_profit + second_profit

    chain.pending_timestamp = days_to_secs(5)
    chain.mine(timestamp=days_to_secs(5))

    assert strategy.totalAssets() == first_profit + second_profit + amount
    strategy.setLoss(fish, first_loss, sender=gov)
    assert strategy.totalAssets() == first_profit + second_profit + amount - first_loss

    dist_rate_profit_1_before_loss = vault.profit_history(0).distribution_rate
    dist_rate_profit_2_before_loss = vault.profit_history(1).distribution_rate

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].loss == first_loss
    assert event[0].total_loss == first_loss
    assert event[0].total_gain == first_profit + second_profit

    assert vault.profit_history(0).distribution_rate < dist_rate_profit_1_before_loss
    assert vault.profit_history(0).distribution_rate < dist_rate_profit_2_before_loss

    chain.pending_timestamp = days_to_secs(10) + 15
    chain.mine(timestamp=days_to_secs(10) + 15)

    vault.update_profit_buffer(sender=gov)

    # All profits should have been unlocked
    with reverts():
        vault.profit_history(0)

    assert vault.totalAssets() == pytest.approx(
        amount + first_profit + second_profit - first_loss, 1e-5
    )
    assert vault.profit_buffer() / 10 ** vault.decimals() == pytest.approx(0, abs=0.5)


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
    Loss is too big for the profit_buffer, so it should drain it and delete before profits from profit_history
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
    vault.process_report(strategy, sender=gov)

    # There should not be any profit on the history
    with pytest.raises(ContractLogicError):
        vault.profit_history(0)

    assert vault.profit_buffer() == 0
    assert vault.totalAssets() == int(10**9 / 2)


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
    Scenario where there is a gain on day 1 of 1000 assets and there are management and performant fess.
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

    assert vault.profit_buffer() == 0
    assert vault.profit_unlock_time() == days_to_secs(7)

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

    first_profit_without_fees = int(
        first_profit * (MAX_BPS - performance_fee) / MAX_BPS
    )
    assert vault.profit_buffer() == first_profit_without_fees
    assert vault.profit_history(0).distribution_rate / MAX_BPS == pytest.approx(
        first_profit_without_fees / int(vault.profit_unlock_time()), 1e-5
    )


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
    Scenario where there is a gain on day 1 of 1000 assets, a deposit on day 2 of 1000 assets and a withdraw
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

    assert vault.profit_buffer() == 0
    assert vault.profit_unlock_time() == days_to_secs(7)

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
    last_update_before_deposit = vault.last_profit_buffer_update()

    vault.deposit(deposit, fish, sender=fish)

    # During the deposit, profit locking values have been updated
    assert last_update_before_deposit < vault.last_profit_buffer_update()
    assert balance_before_deposit < vault.balanceOf(fish)
    assert pps_before_deposit < vault.price_per_share()

    assert vault.totalAssets() + vault.profit_buffer() == amount + 2 * deposit

    # Due to the report of profits, vault pps should be higher: for the same amount, second deposit gives fewer shares
    assert balance_before_deposit > (vault.balanceOf(fish) - balance_before_deposit)

    # We move in time and we keep checking values
    chain.pending_timestamp = days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    balance_before_withdraw = vault.balanceOf(fish)
    last_update_before_withdraw = vault.last_profit_buffer_update()
    pps_before_withdraw = vault.price_per_share()

    vault.withdraw(deposit, fish, fish, [strategy], sender=fish)

    # During the withdrawal, profit locking values have been updated
    assert last_update_before_withdraw < vault.last_profit_buffer_update()
    assert balance_before_withdraw > vault.balanceOf(fish)
    # pps keeps increasing as profits are being released
    assert pps_before_withdraw < vault.price_per_share()

    assert vault.totalAssets() + vault.profit_buffer() == pytest.approx(
        amount + 2 * deposit - withdraw, 1e-6
    )


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

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=days_to_secs(1))

    vault.process_report(strategy, sender=gov)
    assert (
        vault.profit_history(0).end_time
        == days_to_secs(7) + vault.last_profit_buffer_update()
    )
    dist_rate_profit_1 = vault.profit_history(0).distribution_rate

    # We change locking time and create a virtual profit
    new_unlocking_time = days_to_secs(8)
    vault.set_profit_unlock_time(new_unlocking_time, sender=gov)
    asset.transfer(strategy, profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert (
        vault.profit_history(1).end_time
        == new_unlocking_time + vault.last_profit_buffer_update()
    )
    assert vault.profit_history(1).distribution_rate < dist_rate_profit_1
    dist_rate_profit_2 = vault.profit_history(1).distribution_rate

    # We change locking time and create a virtual profit
    new_unlocking_time = days_to_secs(10)
    vault.set_profit_unlock_time(new_unlocking_time, sender=gov)
    asset.transfer(strategy, profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert (
        vault.profit_history(2).end_time
        == new_unlocking_time + vault.last_profit_buffer_update()
    )
    assert vault.profit_history(2).distribution_rate < dist_rate_profit_2


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

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    chain.pending_timestamp = days_to_secs(1)
    chain.mine(timestamp=days_to_secs(1))

    vault.process_report(strategy, sender=gov)
    assert (
        vault.profit_history(0).end_time
        == days_to_secs(7) + vault.last_profit_buffer_update()
    )
    dist_rate_profit_1 = vault.profit_history(0).distribution_rate

    # We change locking time and create a virtual profit
    new_unlocking_time = days_to_secs(6)
    vault.set_profit_unlock_time(new_unlocking_time, sender=gov)
    asset.transfer(strategy, profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert (
        vault.profit_history(1).end_time
        == new_unlocking_time + vault.last_profit_buffer_update()
    )
    assert vault.profit_history(1).distribution_rate > dist_rate_profit_1
    dist_rate_profit_2 = vault.profit_history(1).distribution_rate

    # We change locking time and create a virtual profit
    new_unlocking_time = days_to_secs(4)
    vault.set_profit_unlock_time(new_unlocking_time, sender=gov)
    asset.transfer(strategy, profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    assert (
        vault.profit_history(2).end_time
        == new_unlocking_time + vault.last_profit_buffer_update()
    )
    assert vault.profit_history(2).distribution_rate > dist_rate_profit_2
