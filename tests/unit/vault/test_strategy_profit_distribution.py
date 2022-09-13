from utils.utils import days_to_secs
from utils.constants import MAX_BPS, WEEK, YEAR, DAY
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

    initial_timestamp = chain.pending_timestamp

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
    chain.pending_timestamp = initial_timestamp + days_to_secs(4)
    chain.mine(timestamp=chain.pending_timestamp)

    # There are profits, and values are not updated. We need to estimate
    assert vault.totalAssets() == vault.total_debt()
    assert vault.total_debt() == pytest.approx(
        amount + first_profit / WEEK * days_to_secs(4),
        rel=1e-4,
    )

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = initial_timestamp + days_to_secs(10)
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

    initial_timestamp = chain.pending_timestamp

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
    chain.pending_timestamp = initial_timestamp + days_to_secs(4)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.profit_distribution_rate() == int(first_profit / WEEK * MAX_BPS)

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = initial_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.profit_end_date() < days_to_secs(10) + initial_timestamp
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

    initial_timestamp = chain.pending_timestamp

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
    chain.pending_timestamp = initial_timestamp + days_to_secs(1)
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
    chain.pending_timestamp = initial_timestamp + days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == pytest.approx(
        amount + first_profit / WEEK * days_to_secs(2),
        1e-5,
    )

    chain.pending_timestamp = initial_timestamp + days_to_secs(8) + 15
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

    initial_timestamp = chain.pending_timestamp

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

    chain.pending_timestamp = initial_timestamp + days_to_secs(1)
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
    assert vault.profit_end_date() == pytest.approx(
        days_to_secs(8) + initial_timestamp, abs=5
    )
    profit_end_date_before_second_profit = vault.profit_end_date()

    chain.pending_timestamp = initial_timestamp + days_to_secs(3)
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
    assert vault.profit_end_date() < initial_timestamp + days_to_secs(3) + WEEK

    chain.pending_timestamp = initial_timestamp + days_to_secs(10) + 15
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

    initial_timestamp = chain.pending_timestamp

    vault = create_vault(asset)
    strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    chain.pending_timestamp = initial_timestamp + days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == profit

    assert strategy.totalAssets() == amount + profit

    chain.pending_timestamp = initial_timestamp + days_to_secs(4)
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

    chain.pending_timestamp = initial_timestamp + days_to_secs(10) + 15
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

    initial_timestamp = chain.pending_timestamp

    vault = create_vault(asset)
    strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=fish)

    chain.pending_timestamp = initial_timestamp + days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    chain.pending_timestamp = initial_timestamp + days_to_secs(2)
    chain.mine(timestamp=chain.pending_timestamp)

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
    accountant,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets and there are performance fees.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    """

    amount = 10**9
    profit = 10**9
    management_fee = 0
    performance_fee = 1_000
    total_fees = profit // 10

    initial_timestamp = chain.pending_timestamp

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # set up accountant
    set_fees_for_strategy(gov, strategy, accountant, management_fee, performance_fee)

    assert strategy.totalAssets() == amount
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    initial_total_assets = vault.totalAssets()
    initial_total_supply = vault.totalSupply()

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    assert vault.profit_distribution_rate() == 0

    # We call process_report at t_1
    chain.pending_timestamp = initial_timestamp + days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == profit

    assert vault.totalAssets() == amount + profit * performance_fee / MAX_BPS
    assert vault.total_debt() == amount + profit * performance_fee / MAX_BPS
    assert vault.total_idle() == 0

    profit_without_fees = profit * (MAX_BPS - performance_fee) / MAX_BPS
    assert vault.profit_distribution_rate() / MAX_BPS == pytest.approx(
        profit_without_fees / WEEK, 1e-5
    )

    # Vault unlocks from profit the total_fee amount to avoid decreasing pps because of fees
    share_price_before_minting_fees = (
        initial_total_assets + total_fees
    ) / initial_total_supply
    assert vault.balanceOf(accountant) == int(
        total_fees / share_price_before_minting_fees
    )

    assert vault.price_per_share() / 10 ** vault.decimals() == pytest.approx(
        (initial_total_assets + total_fees)
        / (initial_total_supply + vault.balanceOf(accountant)),
        1e-5,
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
    flexible_accountant,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets and there are performance fees of 100% of profit.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    """

    amount = 10**9
    profit = 10**9
    management_fee = 0
    performance_fee = 10_000
    total_fees = profit

    initial_timestamp = chain.pending_timestamp

    vault = create_vault(asset, accountant=flexible_accountant)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # set up accountant and fees
    set_fees_for_strategy(
        gov, strategy, flexible_accountant, management_fee, performance_fee
    )

    assert strategy.totalAssets() == amount
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    initial_total_assets = vault.totalAssets()
    initial_total_supply = vault.totalSupply()

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    assert vault.profit_distribution_rate() == 0

    # We call process_report at t_1
    chain.pending_timestamp = initial_timestamp + days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == profit

    assert vault.totalAssets() == amount + profit
    assert vault.total_debt() == amount + profit
    assert vault.total_idle() == 0

    assert vault.profit_distribution_rate() == 0

    # Vault unlocks from profit the total_fee amount to avoid decreasing pps because of fees
    share_price_before_minting_fees = (
        initial_total_assets + total_fees
    ) / initial_total_supply
    assert vault.balanceOf(flexible_accountant) == int(
        total_fees / share_price_before_minting_fees
    )

    assert vault.price_per_share() / 10 ** vault.decimals() == pytest.approx(
        (initial_total_assets + total_fees)
        / (initial_total_supply + vault.balanceOf(flexible_accountant)),
        1e-5,
    )


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
    flexible_accountant,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets and there are performance fees of 200% of profit.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    """

    amount = 10**9
    profit = 10**9
    management_fee = 0
    performance_fee = 20_000
    total_fees = profit * 2

    initial_timestamp = chain.pending_timestamp

    vault = create_vault(asset, accountant=flexible_accountant)
    strategy = create_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # set up accountant
    set_fees_for_strategy(
        gov, strategy, flexible_accountant, management_fee, performance_fee
    )

    assert strategy.totalAssets() == amount

    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    initial_total_assets = vault.totalAssets()
    initial_total_supply = vault.totalSupply()

    # We create a virtual profit
    asset.transfer(strategy, profit, sender=fish)

    assert vault.totalAssets() == amount
    assert vault.total_debt() == amount
    assert vault.total_idle() == 0
    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0

    assert vault.profit_distribution_rate() == 0

    # We call process_report at t_1
    chain.pending_timestamp = initial_timestamp + days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == profit

    assert vault.totalAssets() == amount + profit
    assert vault.total_debt() == amount + profit
    assert vault.total_idle() == 0

    assert vault.profit_distribution_rate() == 0

    # Vault unlocks all profit (as total_fees are greater) to avoid decreasing pps as much as possible
    share_price_before_minting_fees = (
        initial_total_assets + profit
    ) / initial_total_supply
    assert vault.balanceOf(flexible_accountant) == int(
        total_fees / share_price_before_minting_fees
    )

    assert vault.price_per_share() / 10 ** vault.decimals() == pytest.approx(
        (initial_total_assets + profit)
        / (initial_total_supply + vault.balanceOf(flexible_accountant)),
        1e-5,
    )


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
    flexible_accountant,
):
    """
    Scenario where there is a gain on day 1 of 1000 assets without fees. After there is another profit
    and there are performance fees of 200% of profit.
    Initially we have 1000 assets and therefore 1000 shares (1:1).
    """

    amount = 10**9
    first_profit = int(5 * 10**9)
    second_profit = int(10**9)
    management_fee = 0
    performance_fee = 20_000

    initial_timestamp = chain.pending_timestamp

    vault = create_vault(asset, accountant=flexible_accountant)
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
    chain.pending_timestamp = initial_timestamp + days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == first_profit

    # set up accountant
    set_fees_for_strategy(
        gov, strategy, flexible_accountant, management_fee, performance_fee
    )

    chain.pending_timestamp = initial_timestamp + days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    dist_rate_before_fees = vault.profit_distribution_rate()
    pps_before_fees = vault.price_per_share()

    # We create a virtual profit
    asset.transfer(strategy, second_profit, sender=fish)
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].gain == second_profit

    # Due to the fact that we were able to pay fees with profit and that there is still profit being
    # distributed, pps increases
    assert vault.price_per_share() > pps_before_fees

    # dist rate gets lowered, but there are still profits being distributed
    assert vault.profit_distribution_rate() < dist_rate_before_fees


def test_profit_distribution__one_loss_with_very_big_fees_and_small_pending_profit(
    gov,
    fish,
    asset,
    create_vault,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    set_fees_for_strategy,
    flexible_accountant,
):
    amount = 10 * 10**9
    profit = int(10**9)
    loss = 2 * profit
    # We have a very big management fee only for testing purposes
    management_fee = MAX_BPS * 100
    performance_fee = 0

    vault = create_vault(asset, accountant=flexible_accountant)
    lossy_strategy = create_lossy_strategy(vault)

    # set up accountant
    set_fees_for_strategy(
        gov, lossy_strategy, flexible_accountant, management_fee, performance_fee
    )

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    initial_timestamp = chain.pending_timestamp
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(lossy_strategy, profit, sender=fish)
    pps_before_profit = vault.price_per_share()

    # We call process_report at t_1
    chain.pending_timestamp = initial_timestamp + DAY
    chain.mine(timestamp=chain.pending_timestamp)

    expected_profit_fees = (
        management_fee
        * vault.strategies(lossy_strategy).current_debt
        * (chain.pending_timestamp - vault.strategies(lossy_strategy).last_report)
        / YEAR
        / MAX_BPS
    )

    tx = vault.process_report(lossy_strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].total_fees == pytest.approx(expected_profit_fees, 1e-4)

    # Fees are so big, that pending profit cannot take it and pps decreases
    assert vault.price_per_share() / 10 ** vault.decimals() < pps_before_profit

    # We create a loss
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    chain.pending_timestamp = initial_timestamp + 2 * DAY
    chain.mine(timestamp=chain.pending_timestamp)

    pps_before_loss = vault.price_per_share()

    expected_management_fees = (
        management_fee
        * vault.strategies(lossy_strategy).current_debt
        * (chain.pending_timestamp - vault.strategies(lossy_strategy).last_report)
        / YEAR
        / MAX_BPS
    )

    tx = vault.process_report(lossy_strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].loss == loss
    assert event[0].total_fees == pytest.approx(expected_management_fees, 1e-5)

    assert vault.totalAssets() == amount + profit - loss
    assert vault.price_per_share() / 10 ** vault.decimals() < pps_before_loss


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

    initial_timestamp = chain.pending_timestamp

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
    chain.pending_timestamp = initial_timestamp + days_to_secs(1)
    chain.mine(timestamp=chain.pending_timestamp)

    vault.process_report(strategy, sender=gov)

    # We move in time and we keep checking values
    chain.pending_timestamp = initial_timestamp + days_to_secs(2)
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
    chain.pending_timestamp = initial_timestamp + days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    balance_before_withdraw = vault.balanceOf(fish)
    pps_before_withdraw = vault.price_per_share()

    vault.withdraw(withdraw, fish, fish, [strategy], sender=fish)

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

    initial_timestamp = chain.pending_timestamp

    vault = create_vault(asset, max_profit_locking_time=0)
    strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    asset.transfer(strategy, profit, sender=fish)
    vault.process_report(strategy, sender=gov)

    chain.pending_timestamp = initial_timestamp + days_to_secs(3)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.profit_distribution_rate() == 0
    assert vault.totalAssets() == pytest.approx(amount + profit, 1e-6)


def test_profit_distribution__one_loss_and_enough_pending_profit_no_fees(
    gov,
    fish,
    asset,
    create_vault,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    set_fees_for_strategy,
    flexible_accountant,
):
    amount = 10 * 10**9
    profit = int(5 * 10**9)
    loss = profit // 2

    vault = create_vault(asset, accountant=flexible_accountant)
    lossy_strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    initial_timestamp = chain.pending_timestamp
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(lossy_strategy, profit, sender=fish)
    pps_before_profit = vault.price_per_share()

    # We call process_report at t_1
    chain.pending_timestamp = initial_timestamp + DAY
    chain.mine(timestamp=chain.pending_timestamp)

    vault.process_report(lossy_strategy, sender=gov)

    assert vault.price_per_share() / 10 ** vault.decimals() == 1.0
    assert vault.profit_distribution_rate() == int(profit / WEEK * MAX_BPS)

    distribution_rate_bef_loss = vault.profit_distribution_rate()

    # We create a loss
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    chain.pending_timestamp = initial_timestamp + 2 * DAY
    chain.mine(timestamp=chain.pending_timestamp)

    pps_before_loss = vault.price_per_share()

    tx = vault.process_report(lossy_strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].loss == loss
    assert event[0].total_fees == 0

    # Profit distribution dumps loss and therefore its distribution rate is lower...
    pending_profit_bef_loss = distribution_rate_bef_loss * (WEEK - DAY) / MAX_BPS
    assert vault.profit_distribution_rate() == int(
        (pending_profit_bef_loss - loss) / (WEEK - DAY) * MAX_BPS
    )

    # Price per share does not decrease, it actually increases as some profit gets unlocked
    assert vault.price_per_share() > pps_before_loss
    assert vault.totalAssets() == int(
        amount + distribution_rate_bef_loss * DAY / MAX_BPS
    )

    chain.pending_timestamp = initial_timestamp + 10 * DAY
    chain.mine(timestamp=chain.pending_timestamp)

    # Once all profit has been unlocked...
    assert vault.totalAssets() == pytest.approx(amount + profit - loss, 1e-5)


def test_profit_distribution__one_loss_and_enough_pending_profit_and_small_fees(
    gov,
    fish,
    asset,
    create_vault,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    set_fees_for_strategy,
    flexible_accountant,
):
    amount = 10 * 10**9
    profit = int(5 * 10**9)
    loss = profit // 2
    management_fee = 0
    performance_fee = 1000

    vault = create_vault(asset, accountant=flexible_accountant)
    lossy_strategy = create_lossy_strategy(vault)

    # deposit assets to vault and prepare strategy
    user_deposit(fish, vault, asset, amount)
    initial_timestamp = chain.pending_timestamp
    add_strategy_to_vault(gov, lossy_strategy, vault)
    add_debt_to_strategy(gov, lossy_strategy, vault, amount)

    # set up accountant
    set_fees_for_strategy(
        gov, lossy_strategy, flexible_accountant, management_fee, performance_fee
    )

    # We create a virtual profit
    asset.transfer(lossy_strategy, profit, sender=fish)
    pps_before_profit = vault.price_per_share()

    # We call process_report at t_1
    chain.pending_timestamp = initial_timestamp + DAY
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(lossy_strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    expected_performance_fee = performance_fee * profit / MAX_BPS

    assert event[0].total_fees == pytest.approx(expected_performance_fee, 1e-5)

    # pps increases a bit, due to the minting of fees and the releasing of profit to avoid pps decreasing; as fees
    # are minted at a more expensive price
    assert vault.price_per_share() > pps_before_profit
    assert vault.profit_distribution_rate() == pytest.approx(
        (profit - expected_performance_fee) / WEEK * MAX_BPS, 1e-5
    )

    distribution_rate_bef_loss = vault.profit_distribution_rate()
    pps_before_loss = vault.price_per_share()

    # We create a loss
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    chain.pending_timestamp = initial_timestamp + 2 * DAY
    chain.mine(timestamp=chain.pending_timestamp)

    tx = vault.process_report(lossy_strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert len(event) == 1
    assert event[0].loss == loss
    assert event[0].total_fees == 0

    # Profit distribution dumps loss and therefore its distribution rate is lower...
    pending_profit_bef_loss = distribution_rate_bef_loss * (WEEK - DAY) / MAX_BPS
    assert vault.profit_distribution_rate() == int(
        (pending_profit_bef_loss - loss) / (WEEK - DAY) * MAX_BPS
    )

    # Price per share does not decrease, it actually increases as some profit gets unlocked
    assert vault.price_per_share() > pps_before_loss
    unlocked = profit - pending_profit_bef_loss
    assert vault.totalAssets() == pytest.approx(amount + unlocked, 1e-5)

    chain.pending_timestamp = initial_timestamp + 10 * DAY
    chain.mine(timestamp=chain.pending_timestamp)

    # Once all profit has been unlocked...
    assert vault.totalAssets() == pytest.approx(amount + profit - loss, 1e-5)

    assert vault.totalAssets() == pytest.approx(
        vault.convertToAssets(vault.balanceOf(flexible_accountant))
        + vault.convertToAssets(vault.balanceOf(fish)),
        1e-5,
    )
