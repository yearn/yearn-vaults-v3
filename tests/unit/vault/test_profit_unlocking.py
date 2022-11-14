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
    assert (
        pytest.approx(vault.totalSupply(), rel=1e-5)
        == post_profit_totalSupply - first_profit * days_to_secs(4) / WEEK
    )

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.totalAssets() == vault.total_debt()
    assert vault.total_debt() == amount + first_profit
    assert pytest.approx(vault.totalSupply(), rel=1e-5) == amount


def test_gain_no_fees_no_refunds_no_existing_buffer(
    create_vault,
    asset,
    fish_amount,
    create_strategy,
    user_deposit,
    fish,
    add_strategy_to_vault,
    add_debt_to_strategy,
    gov,
    airdrop_asset,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10

    vault = create_vault(asset)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0], strategy.address, first_profit, 0, amount + first_profit, 0, 0
    )
    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == first_profit

    assert vault.totalSupply() == amount + first_profit
    assert vault.totalAssets() == amount + first_profit

    # We increase time after profit has been released and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0
    assert_price_per_share(vault, 2.0)

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert_price_per_share(vault, 2.0)
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit
    assert vault.totalSupply() == amount
    assert vault.totalAssets() == amount + first_profit

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, 1.0)
    assert vault.total_debt() == 0
    assert vault.total_idle() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert asset.balanceOf(fish) == fish_amount + first_profit


def test_gain_no_fees_no_refunds_with_buffer(
    create_vault,
    asset,
    fish_amount,
    create_strategy,
    user_deposit,
    fish,
    add_strategy_to_vault,
    add_debt_to_strategy,
    gov,
    airdrop_asset,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10
    second_profit = fish_amount // 10

    vault = create_vault(asset)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0], strategy.address, first_profit, 0, amount + first_profit, 0, 0
    )
    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == first_profit

    assert vault.totalSupply() == amount + first_profit
    assert vault.totalAssets() == amount + first_profit

    # We increase time after profit has been released and create a second profit
    chain.pending_timestamp = chain.pending_timestamp + WEEK // 2
    chain.mine(timestamp=chain.pending_timestamp)

    assert pytest.approx(vault.balanceOf(vault), rel=1e-3) == first_profit // 2
    price_per_share = vault.totalAssets() / (amount + first_profit - first_profit // 2)
    assert_price_per_share(vault, price_per_share)

    asset.transfer(strategy, second_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        second_profit,
        0,
        amount + first_profit + second_profit,
        0,
        0,
    )
    # pps doesn't change as profit goes directly to buffer
    assert_price_per_share(vault, price_per_share)
    assert pytest.approx(
        vault.balanceOf(vault), rel=1e-3
    ) == first_profit // 2 + vault.convertToShares(second_profit)

    assert pytest.approx(
        vault.totalSupply(), rel=1e-4
    ) == amount + first_profit // 2 + vault.convertToShares(second_profit)
    assert vault.totalAssets() == amount + first_profit + second_profit

    # We increase time and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0
    assert_price_per_share(vault, 3.0)

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert_price_per_share(vault, 3.0)
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit + second_profit
    assert vault.totalSupply() == amount
    assert vault.totalAssets() == amount + first_profit + second_profit

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, 1.0)
    assert vault.total_debt() == 0
    assert vault.total_idle() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert asset.balanceOf(fish) == fish_amount + first_profit + second_profit


def test_loss_no_fees_no_refunds_no_existing_buffer(
    create_vault,
    asset,
    fish_amount,
    create_lossy_strategy,
    user_deposit,
    fish,
    add_strategy_to_vault,
    add_debt_to_strategy,
    gov,
    airdrop_asset,
):
    amount = fish_amount // 10
    first_loss = fish_amount // 20

    vault = create_vault(asset)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_lossy_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual loss
    strategy.setLoss(gov, first_loss, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0], strategy.address, 0, first_loss, amount - first_loss, 0, 0
    )
    assert_price_per_share(vault, 0.5)
    assert vault.balanceOf(vault) == 0

    assert vault.totalSupply() == amount
    assert vault.totalAssets() == amount - first_loss

    # Update strategy debt to 0
    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert_price_per_share(vault, 0.5)
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount - first_loss
    assert vault.totalSupply() == amount
    assert vault.totalAssets() == amount - first_loss

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, 1.0)
    assert vault.total_debt() == 0
    assert vault.total_idle() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert asset.balanceOf(fish) == fish_amount - first_loss


def test_loss_no_fees_no_refunds_with_buffer(
    create_vault,
    asset,
    fish_amount,
    create_lossy_strategy,
    user_deposit,
    fish,
    add_strategy_to_vault,
    add_debt_to_strategy,
    gov,
    airdrop_asset,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10
    first_loss = fish_amount // 50

    vault = create_vault(asset)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_lossy_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0], strategy.address, first_profit, 0, amount + first_profit, 0, 0
    )
    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == first_profit

    assert vault.totalSupply() == amount + first_profit
    assert vault.totalAssets() == amount + first_profit

    # We increase time and create a loss
    chain.pending_timestamp = chain.pending_timestamp + WEEK // 2
    chain.mine(timestamp=chain.pending_timestamp)

    assert pytest.approx(vault.balanceOf(vault), rel=1e-3) == first_profit // 2
    price_per_share = vault.totalAssets() / (amount + first_profit - first_profit // 2)
    assert_price_per_share(vault, price_per_share)

    assert (
        pytest.approx(vault.totalSupply(), rel=1e-3)
        == amount + first_profit - first_profit // 2
    )
    assert vault.totalAssets() == amount + first_profit

    # We create a virtual loss that doesn't change pps as its taken care by profit buffer
    strategy.setLoss(gov, first_loss, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        0,
        first_loss,
        amount + first_profit - first_loss,
        0,
        0,
    )
    assert pytest.approx(
        vault.balanceOf(vault), rel=1e-3
    ) == first_profit // 2 - vault.convertToShares(first_loss)
    assert_price_per_share(vault, price_per_share)

    assert pytest.approx(
        vault.totalSupply(), rel=1e-3
    ) == amount + first_profit - first_profit // 2 - vault.convertToShares(first_loss)
    assert vault.totalAssets() == amount + first_profit - first_loss

    # We increase time and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0
    assert_price_per_share(vault, (amount + first_profit - first_loss) / amount)

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert_price_per_share(vault, (amount + first_profit - first_loss) / amount)
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit - first_loss
    assert vault.totalSupply() == amount
    assert vault.totalAssets() == amount + first_profit - first_loss

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, 1.0)
    assert vault.total_debt() == 0
    assert vault.total_idle() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert asset.balanceOf(fish) == fish_amount + first_profit - first_loss


def test_loss_no_fees_no_refunds_with_not_enough_buffer(
    create_vault,
    asset,
    fish_amount,
    create_lossy_strategy,
    user_deposit,
    fish,
    add_strategy_to_vault,
    add_debt_to_strategy,
    gov,
    airdrop_asset,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 20
    first_loss = fish_amount // 10

    vault = create_vault(asset)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_lossy_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0], strategy.address, first_profit, 0, amount + first_profit, 0, 0
    )
    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == first_profit

    assert vault.totalSupply() == amount + first_profit
    assert vault.totalAssets() == amount + first_profit

    # We increase time and create a loss
    chain.pending_timestamp = chain.pending_timestamp + WEEK // 2
    chain.mine(timestamp=chain.pending_timestamp)

    assert pytest.approx(vault.balanceOf(vault), rel=1e-3) == first_profit // 2
    price_per_share = vault.totalAssets() / (amount + first_profit - first_profit // 2)
    assert_price_per_share(vault, price_per_share)

    assert (
        pytest.approx(vault.totalSupply(), rel=1e-3)
        == amount + first_profit - first_profit // 2
    )
    assert vault.totalAssets() == amount + first_profit

    # We create a virtual loss. pps is affected as there is not enough buffer
    strategy.setLoss(gov, first_loss, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        0,
        first_loss,
        amount + first_profit - first_loss,
        0,
        0,
    )
    assert pytest.approx(vault.balanceOf(vault), abs=1) == 0
    assert vault.totalSupply() == amount + vault.balanceOf(vault)
    assert vault.totalAssets() == amount + first_profit - first_loss

    assert_price_per_share(vault, (amount + first_profit - first_loss) / amount)

    # We increase time and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0
    assert_price_per_share(vault, (amount + first_profit - first_loss) / amount)

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert_price_per_share(vault, (amount + first_profit - first_loss) / amount)
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit - first_loss
    assert vault.totalSupply() == amount
    assert vault.totalAssets() == amount + first_profit - first_loss

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, 1.0)
    assert vault.total_debt() == 0
    assert vault.total_idle() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert asset.balanceOf(fish) == fish_amount + first_profit - first_loss


def assert_strategy_reported(
    log, strategy_address, gain, loss, current_debt, total_fees, total_refunds
):
    assert log.strategy == strategy_address
    assert log.gain == gain
    assert log.loss == loss
    assert log.current_debt == current_debt
    assert log.total_fees == total_fees
    assert log.total_refunds == total_refunds


def assert_price_per_share(vault, pps):
    assert (
        pytest.approx(vault.price_per_share() / 10 ** vault.decimals(), rel=1e-4) == pps
    )
