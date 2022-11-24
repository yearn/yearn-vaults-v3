from utils.utils import days_to_secs
from utils.constants import MAX_BPS, MAX_BPS_ACCOUNTANT, WEEK, YEAR, DAY
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


def test_gain_no_fees_with_refunds_accountant_not_enough_shares(
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
    deploy_flexible_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10

    management_fee = 0
    performance_fee = 0
    refund_ratio = 10_000

    vault = create_vault(asset)
    accountant = deploy_flexible_accountant(vault)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_strategy(vault)

    set_fees_for_strategy(
        gov,
        strategy,
        accountant,
        management_fee,
        performance_fee,
        refund_ratio=refund_ratio,
    )

    airdrop_asset(gov, asset, accountant, fish_amount)
    user_deposit(accountant, vault, asset, first_profit // 10)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert event[0].total_refunds != first_profit * refund_ratio / MAX_BPS_ACCOUNTANT
    assert_strategy_reported(
        event[0],
        strategy.address,
        first_profit,
        0,
        amount + first_profit,
        0,
        first_profit // 10,
    )

    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == first_profit + first_profit // 10

    assert vault.totalSupply() == amount + first_profit + first_profit // 10
    assert vault.totalAssets() == amount + first_profit + first_profit // 10


def test_gain_no_fees_with_refunds(
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
    deploy_flexible_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10

    management_fee = 0
    performance_fee = 0
    refund_ratio = 10_000

    vault = create_vault(asset)
    accountant = deploy_flexible_accountant(vault)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_strategy(vault)

    set_fees_for_strategy(
        gov,
        strategy,
        accountant,
        management_fee,
        performance_fee,
        refund_ratio=refund_ratio,
    )

    # Accountant deposits to be able to refund
    airdrop_asset(gov, asset, accountant, fish_amount)
    user_deposit(accountant, vault, asset, amount)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        first_profit,
        0,
        amount + first_profit,
        0,
        first_profit * refund_ratio / MAX_BPS_ACCOUNTANT,
    )

    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == first_profit * (
        1 + refund_ratio / MAX_BPS_ACCOUNTANT
    )
    assert vault.totalSupply() == amount + first_profit * (
        1 + refund_ratio / MAX_BPS_ACCOUNTANT
    )
    assert vault.totalAssets() == 2 * amount + first_profit

    assert vault.balanceOf(vault) == first_profit * (
        1 + refund_ratio / MAX_BPS_ACCOUNTANT
    )
    assert (
        vault.balanceOf(accountant)
        == amount - first_profit * refund_ratio / MAX_BPS_ACCOUNTANT
    )

    # We increase time after profit has been released and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0
    assert vault.totalSupply() == amount
    assert vault.price_per_share() / 10 ** vault.decimals() == 3.0

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert vault.price_per_share() / 10 ** vault.decimals() == 3.0
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit * (
        1 + refund_ratio / MAX_BPS_ACCOUNTANT
    )

    assert vault.totalSupply() == amount
    assert vault.totalAssets() == 2 * amount + first_profit

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, 1.0)
    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == fish_amount + first_profit * (
        1 + refund_ratio / MAX_BPS_ACCOUNTANT
    )

    # Accountant redeems shares
    with reverts("no shares to redeem"):
        vault.redeem(
            vault.balanceOf(accountant), accountant, accountant, [], sender=accountant
        )


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


def test_gain_fees_no_refunds_no_existing_buffer(
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
    deploy_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10
    # Using only performance_fee as its easier to measure for tests
    management_fee = 0
    performance_fee = 1_000

    vault = create_vault(asset)
    accountant = deploy_accountant(vault)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_strategy(vault)

    set_fees_for_strategy(
        gov, strategy, accountant, management_fee, performance_fee, refund_ratio=0
    )

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        first_profit,
        0,
        amount + first_profit,
        performance_fee * first_profit / MAX_BPS_ACCOUNTANT,
        0,
    )
    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == first_profit * (
        1 - performance_fee / MAX_BPS_ACCOUNTANT
    )
    fee_shares = first_profit * (performance_fee / MAX_BPS_ACCOUNTANT)
    assert vault.balanceOf(accountant) == fee_shares

    assert vault.totalSupply() == amount + first_profit
    assert vault.totalAssets() == amount + first_profit

    # We increase time after profit has been released and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0
    assert vault.price_per_share() / 10 ** vault.decimals() < 2.0

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert vault.price_per_share() / 10 ** vault.decimals() < 2.0
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit

    assert vault.totalSupply() == amount + fee_shares
    assert vault.totalAssets() == amount + first_profit

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, vault.totalAssets() / vault.balanceOf(accountant))
    assert vault.total_debt() == 0
    assert vault.totalSupply() == first_profit * (performance_fee / MAX_BPS_ACCOUNTANT)
    assert fish_amount < asset.balanceOf(fish)
    assert asset.balanceOf(fish) < fish_amount + first_profit

    # Accountant redeems shares
    vault.redeem(
        vault.balanceOf(accountant), accountant, accountant, [], sender=accountant
    )

    assert vault.total_idle() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0
    assert (
        asset.balanceOf(accountant) + asset.balanceOf(fish)
        == fish_amount + first_profit
    )


def test_gain_fees_refunds_no_existing_buffer(
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
    deploy_flexible_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10
    # Using only performance_fee as its easier to measure for tests
    management_fee = 0
    performance_fee = 1_000
    refund_ratio = 10_000

    vault = create_vault(asset)
    accountant = deploy_flexible_accountant(vault)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_strategy(vault)

    set_fees_for_strategy(
        gov, strategy, accountant, management_fee, performance_fee, refund_ratio
    )

    airdrop_asset(gov, asset, accountant, fish_amount)
    user_deposit(accountant, vault, asset, amount)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        first_profit,
        0,
        amount + first_profit,
        performance_fee * first_profit / MAX_BPS_ACCOUNTANT,
        first_profit * refund_ratio / MAX_BPS_ACCOUNTANT,
    )
    assert_price_per_share(vault, 1.0)
    assert (
        vault.balanceOf(vault)
        == first_profit * (1 - performance_fee / MAX_BPS_ACCOUNTANT)
        + first_profit * refund_ratio / MAX_BPS_ACCOUNTANT
    )

    fee_shares = first_profit * performance_fee / MAX_BPS_ACCOUNTANT
    assert (
        vault.balanceOf(accountant)
        == amount - first_profit * refund_ratio / MAX_BPS_ACCOUNTANT + fee_shares
    )

    assert (
        vault.totalSupply()
        == amount + first_profit + first_profit * refund_ratio / MAX_BPS_ACCOUNTANT
    )
    assert (
        vault.balanceOf(vault)
        == first_profit
        + first_profit * refund_ratio / MAX_BPS_ACCOUNTANT
        - performance_fee * first_profit / MAX_BPS_ACCOUNTANT
    )
    assert vault.totalAssets() == 2 * amount + first_profit

    # We increase time after profit has been released and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0
    assert pytest.approx(
        vault.price_per_share() / 10 ** vault.decimals(), rel=1e-4
    ) == (2 * amount + first_profit) / (amount + fee_shares)

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert pytest.approx(
        vault.price_per_share() / 10 ** vault.decimals(), rel=1e-4
    ) == (2 * amount + first_profit) / (amount + fee_shares)
    assert vault.total_debt() == 0
    assert vault.total_idle() == 2 * amount + first_profit

    assert vault.totalSupply() == amount + fee_shares
    assert vault.totalAssets() == 2 * amount + first_profit

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, vault.totalAssets() / vault.balanceOf(accountant))
    assert vault.total_debt() == 0
    assert vault.totalSupply() == first_profit * (performance_fee / MAX_BPS_ACCOUNTANT)
    assert fish_amount < asset.balanceOf(fish)

    assert (
        pytest.approx(asset.balanceOf(fish), abs=1)
        == fish_amount
        + (2 * amount + first_profit) / (amount + fee_shares) * amount
        - amount
    )

    # Accountant redeems shares
    vault.redeem(
        vault.balanceOf(accountant), accountant, accountant, [], sender=accountant
    )

    assert vault.total_idle() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0
    assert (
        asset.balanceOf(accountant) + asset.balanceOf(fish)
        == 2 * fish_amount + first_profit
    )


def test_gain_fees_no_refunds_with_buffer(
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
    deploy_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10
    second_profit = fish_amount // 10
    # Using only performance_fee as its easier to measure for tests
    management_fee = 0
    performance_fee = 1_000

    vault = create_vault(asset)
    accountant = deploy_accountant(vault)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_strategy(vault)

    set_fees_for_strategy(
        gov, strategy, accountant, management_fee, performance_fee, refund_ratio=0
    )

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        first_profit,
        0,
        amount + first_profit,
        performance_fee * first_profit / MAX_BPS_ACCOUNTANT,
        0,
    )
    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == first_profit * (
        1 - performance_fee / MAX_BPS_ACCOUNTANT
    )
    fee_shares = first_profit * (performance_fee / MAX_BPS_ACCOUNTANT)
    assert vault.balanceOf(accountant) == fee_shares

    assert vault.totalSupply() == amount + first_profit
    assert vault.totalAssets() == amount + first_profit

    # We increase time after profit has been released and create a second profit
    chain.pending_timestamp = chain.pending_timestamp + WEEK // 2
    chain.mine(timestamp=chain.pending_timestamp)

    assert (
        pytest.approx(vault.balanceOf(vault), rel=1e-3)
        == first_profit * (1 - performance_fee / MAX_BPS_ACCOUNTANT) // 2
    )
    # price_per_share = vault.totalAssets() / (amount + first_profit / 2 + first_profit * (performance_fee / MAX_BPS_ACCOUNTANT))
    # assert_price_per_share(vault, price_per_share)

    price_per_share_before_2nd_profit = vault.price_per_share() / 10 ** vault.decimals()
    accountant_shares_before_2nd_profit = vault.balanceOf(accountant)
    vault_shares_before_2nd_profit = vault.balanceOf(vault)

    asset.transfer(strategy, second_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        second_profit,
        0,
        amount + first_profit + second_profit,
        second_profit * performance_fee // MAX_BPS_ACCOUNTANT,
        0,
    )
    # # pps doesn't change as profit goes directly to buffer and fees are damped
    assert_price_per_share(vault, price_per_share_before_2nd_profit)

    assert vault.balanceOf(
        accountant
    ) == accountant_shares_before_2nd_profit + vault.convertToShares(
        second_profit * performance_fee // MAX_BPS_ACCOUNTANT
    )

    assert pytest.approx(
        vault.balanceOf(vault), 1e-4
    ) == vault_shares_before_2nd_profit + vault.convertToShares(
        int(second_profit * (1 - performance_fee / MAX_BPS_ACCOUNTANT))
    )

    assert (
        pytest.approx(vault.totalSupply(), rel=1e-3)
        == amount
        + first_profit * performance_fee / MAX_BPS_ACCOUNTANT
        + vault.convertToShares(second_profit)
        + first_profit * (1 - performance_fee / MAX_BPS_ACCOUNTANT) // 2
    )

    assert vault.totalAssets() == amount + first_profit + second_profit

    # We increase time and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0
    # pps is not as big as fees lower it
    assert vault.price_per_share() / 10 ** vault.decimals() < 3.0

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert vault.price_per_share() / 10 ** vault.decimals() < 3.0
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit + second_profit
    assert vault.totalSupply() == amount + vault.balanceOf(accountant)
    assert vault.totalAssets() == amount + first_profit + second_profit

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, vault.totalAssets() / vault.balanceOf(accountant))
    assert vault.total_debt() == 0

    assert fish_amount < asset.balanceOf(fish)
    assert asset.balanceOf(fish) < fish_amount + first_profit + second_profit

    # Accountant redeems shares
    vault.redeem(
        vault.balanceOf(accountant), accountant, accountant, [], sender=accountant
    )
    assert vault.total_idle() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0
    assert (
        asset.balanceOf(accountant) + asset.balanceOf(fish)
        == fish_amount + first_profit + second_profit
    )


def test_gain_fees_no_refunds_not_enough_buffer(
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
    deploy_flexible_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10
    second_profit = fish_amount // 10
    # Using only performance_fee as its easier to measure for tests
    management_fee = 0
    first_performance_fee = 1_000
    # Huge fee that profit cannot damp
    second_performance_fee = 50_000

    vault = create_vault(asset)
    accountant = deploy_flexible_accountant(vault)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_strategy(vault)

    set_fees_for_strategy(
        gov, strategy, accountant, management_fee, first_performance_fee, refund_ratio=0
    )
    assert accountant.fees(strategy).performance_fee == first_performance_fee

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual profit
    asset.transfer(strategy, first_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        first_profit,
        0,
        amount + first_profit,
        first_performance_fee * first_profit / MAX_BPS_ACCOUNTANT,
        0,
    )
    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == first_profit * (
        1 - first_performance_fee / MAX_BPS_ACCOUNTANT
    )
    fee_shares = first_profit * (first_performance_fee / MAX_BPS_ACCOUNTANT)
    assert vault.balanceOf(accountant) == fee_shares

    assert vault.totalSupply() == amount + first_profit
    assert vault.totalAssets() == amount + first_profit

    # We increase time after profit has been released and create a second profit
    chain.pending_timestamp = chain.pending_timestamp + WEEK // 2
    chain.mine(timestamp=chain.pending_timestamp)

    assert (
        pytest.approx(vault.balanceOf(vault), rel=1e-3)
        == first_profit * (1 - first_performance_fee / MAX_BPS_ACCOUNTANT) // 2
    )

    price_per_share_before_2nd_profit = vault.price_per_share() / 10 ** vault.decimals()
    accountant_shares_before_2nd_profit = vault.balanceOf(accountant)

    # Increase fees to create a huge fee
    set_fees_for_strategy(
        gov,
        strategy,
        accountant,
        management_fee,
        second_performance_fee,
        refund_ratio=0,
    )
    assert accountant.fees(strategy).performance_fee == second_performance_fee

    asset.transfer(strategy, second_profit, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0],
        strategy.address,
        second_profit,
        0,
        amount + first_profit + second_profit,
        second_profit * second_performance_fee // MAX_BPS_ACCOUNTANT,
        0,
    )
    # # pps doesn't change as profit goes directly to buffer and fees are damped
    assert (
        vault.price_per_share() / 10 ** vault.decimals()
        < price_per_share_before_2nd_profit
    )

    assert (
        pytest.approx(vault.balanceOf(accountant), rel=1e-4)
        == accountant_shares_before_2nd_profit
        + second_profit
        * second_performance_fee
        // MAX_BPS_ACCOUNTANT
        / price_per_share_before_2nd_profit
    )

    assert vault.balanceOf(vault) == 0

    assert vault.totalAssets() == amount + first_profit + second_profit

    # We update strategy debt to 0
    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert vault.price_per_share() / 10 ** vault.decimals() < 1.0
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit + second_profit
    assert vault.totalSupply() == amount + vault.balanceOf(accountant)
    assert vault.totalAssets() == amount + first_profit + second_profit

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, vault.totalAssets() / vault.balanceOf(accountant))
    assert vault.total_debt() == 0

    assert asset.balanceOf(fish) < fish_amount

    # Accountant redeems shares
    vault.redeem(
        vault.balanceOf(accountant), accountant, accountant, [], sender=accountant
    )
    assert vault.total_idle() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0
    assert (
        asset.balanceOf(accountant) + asset.balanceOf(fish)
        == fish_amount + first_profit + second_profit
    )


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


def test_loss_fees_no_refunds_no_existing_buffer(
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
    deploy_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_loss = fish_amount // 20

    management_fee = 10_000
    performance_fee = 0

    vault = create_vault(asset)
    accountant = deploy_accountant(vault)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_lossy_strategy(vault)

    set_fees_for_strategy(
        gov, strategy, accountant, management_fee, performance_fee, refund_ratio=0
    )

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # We create a virtual loss
    strategy.setLoss(gov, first_loss, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert event[0].total_fees > 0
    assert vault.price_per_share() / 10 ** vault.decimals() < 0.5
    assert vault.balanceOf(vault) == 0

    assert vault.totalSupply() > amount
    assert vault.totalAssets() == amount - first_loss

    # Update strategy debt to 0
    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert vault.price_per_share() / 10 ** vault.decimals() < 0.5
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount - first_loss
    assert vault.totalSupply() > amount
    assert vault.totalAssets() == amount - first_loss

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert vault.total_debt() == 0
    assert vault.totalSupply() == vault.balanceOf(accountant)
    assert asset.balanceOf(vault) == vault.convertToAssets(vault.balanceOf(accountant))

    assert asset.balanceOf(fish) < fish_amount - first_loss

    # Accountant redeems shares
    vault.redeem(
        vault.balanceOf(accountant), accountant, accountant, [], sender=accountant
    )

    assert vault.total_debt() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert (
        asset.balanceOf(accountant) + asset.balanceOf(fish) == fish_amount - first_loss
    )


def test_loss_no_fees_refunds_no_existing_buffer(
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
    deploy_flexible_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_loss = fish_amount // 10

    management_fee = 0
    performance_fee = 0
    refund_ratio = 10_000  # 100%

    vault = create_vault(asset)
    accountant = deploy_flexible_accountant(vault)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_lossy_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    set_fees_for_strategy(
        gov, strategy, accountant, management_fee, performance_fee, refund_ratio
    )
    airdrop_asset(gov, asset, accountant, fish_amount)
    user_deposit(accountant, vault, asset, amount)

    assert vault.totalSupply() == 2 * amount
    assert vault.totalAssets() == 2 * amount

    # We create a virtual loss
    strategy.setLoss(gov, first_loss, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert_strategy_reported(
        event[0], strategy.address, 0, first_loss, amount - first_loss, 0, first_loss
    )
    assert_price_per_share(vault, 1.0)
    assert vault.balanceOf(vault) == 0

    assert vault.totalSupply() == amount
    assert vault.totalAssets() == amount

    assert vault.balanceOf(accountant) == 0

    # Update strategy debt to 0
    with reverts("new debt equals current debt"):
        add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert_price_per_share(vault, 1.0)
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount
    assert vault.totalSupply() == amount
    assert vault.totalAssets() == amount

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert_price_per_share(vault, 1.0)
    assert vault.total_debt() == 0
    assert vault.total_idle() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert asset.balanceOf(fish) == fish_amount


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

    # We increase time
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


def test_loss_fees_no_refunds_with_buffer(
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
    deploy_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10
    first_loss = fish_amount // 50

    management_fee = 500
    performance_fee = 0

    vault = create_vault(asset)
    accountant = deploy_accountant(vault)
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

    # We set fees after profit to simplify example
    set_fees_for_strategy(
        gov, strategy, accountant, management_fee, performance_fee, refund_ratio=0
    )

    # We create a virtual loss that doesn't change pps as its taken care by profit buffer
    strategy.setLoss(gov, first_loss, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert event[0].total_fees > 0
    # pps is not affected by fees
    assert (
        pytest.approx(price_per_share, rel=1e-3)
        == vault.price_per_share() / 10 ** vault.decimals()
    )
    assert vault.balanceOf(vault) < first_profit // 2

    assert vault.totalAssets() == amount + first_profit - first_loss
    assert vault.totalSupply() > amount
    assert (
        vault.totalSupply() < amount + first_profit / 2
    )  # Because we have burned shares

    # We increase time and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0

    # pps is slightly lower due to fees
    assert (
        vault.price_per_share() / 10 ** vault.decimals()
        < (amount + first_profit - first_loss) / amount
    )

    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit - first_loss
    assert vault.totalSupply() > amount  # Due to fees
    assert vault.totalAssets() == amount + first_profit - first_loss

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert vault.total_debt() == 0
    assert vault.totalSupply() == vault.balanceOf(accountant)
    assert asset.balanceOf(vault) == vault.convertToAssets(vault.balanceOf(accountant))

    assert asset.balanceOf(fish) < fish_amount + first_profit - first_loss
    assert asset.balanceOf(fish) > fish_amount

    # Accountant redeems shares
    vault.redeem(
        vault.balanceOf(accountant), accountant, accountant, [], sender=accountant
    )

    assert vault.total_debt() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert (
        asset.balanceOf(accountant) + asset.balanceOf(fish)
        == fish_amount + first_profit - first_loss
    )


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
    assert vault.balanceOf(vault) == 0
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


def test_loss_fees_no_refunds_with_not_enough_buffer(
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
    deploy_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_profit = fish_amount // 20
    first_loss = fish_amount // 10

    management_fee = 500
    performance_fee = 0

    vault = create_vault(asset)
    accountant = deploy_accountant(vault)
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

    # We set fees after profit to simplify example
    set_fees_for_strategy(
        gov, strategy, accountant, management_fee, performance_fee, refund_ratio=0
    )

    # We increase time
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

    assert event[0].total_fees > 0
    assert event[0].current_debt == amount + first_profit - first_loss
    assert vault.balanceOf(vault) == 0
    assert vault.totalSupply() == amount + vault.balanceOf(accountant)
    assert vault.totalAssets() == amount + first_profit - first_loss

    assert (
        vault.price_per_share() / 10 ** vault.decimals()
        < (amount + first_profit - first_loss) / amount
    )
    assert pytest.approx(
        vault.price_per_share() / 10 ** vault.decimals(), rel=1e-4
    ) == (amount + first_profit - first_loss) / (
        amount + event[0].total_fees / price_per_share
    )
    price_per_share = vault.price_per_share() / 10 ** vault.decimals()

    # We increase time and update strategy debt to 0
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.balanceOf(vault) == 0
    assert_price_per_share(vault, price_per_share)

    add_debt_to_strategy(gov, strategy, vault, 0)

    assert vault.strategies(strategy).current_debt == 0
    assert_price_per_share(vault, price_per_share)
    assert vault.total_debt() == 0
    assert vault.total_idle() == amount + first_profit - first_loss
    assert vault.totalSupply() == amount + vault.balanceOf(accountant)
    assert vault.totalAssets() == amount + first_profit - first_loss

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert vault.total_debt() == 0
    assert vault.totalSupply() == vault.balanceOf(accountant)
    assert asset.balanceOf(vault) == vault.convertToAssets(vault.balanceOf(accountant))

    assert asset.balanceOf(fish) < fish_amount
    assert asset.balanceOf(fish) < fish_amount + first_profit - first_loss

    # Accountant redeems shares
    vault.redeem(
        vault.balanceOf(accountant), accountant, accountant, [], sender=accountant
    )

    assert vault.total_debt() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert (
        asset.balanceOf(accountant) + asset.balanceOf(fish)
        == fish_amount + first_profit - first_loss
    )


def test_loss_fees_refunds(
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
    deploy_accountant,
    set_fees_for_strategy,
):
    amount = fish_amount // 10
    first_loss = fish_amount // 10

    management_fee = 500
    performance_fee = 0
    refund_ratio = 10_000  # Losses are covered 100%

    vault = create_vault(asset)
    accountant = deploy_accountant(vault)
    airdrop_asset(gov, asset, gov, fish_amount)
    strategy = create_lossy_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    set_fees_for_strategy(
        gov, strategy, accountant, management_fee, performance_fee, refund_ratio
    )
    airdrop_asset(gov, asset, accountant, fish_amount)
    user_deposit(accountant, vault, asset, amount)

    assert vault.totalAssets() == 2 * amount

    # We create a virtual loss. pps is affected as there is not enough buffer
    strategy.setLoss(gov, first_loss, sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert event[0].total_fees > 0
    assert event[0].current_debt == 0
    assert vault.balanceOf(vault) == 0
    assert vault.balanceOf(accountant) > 0
    assert vault.balanceOf(accountant) == event[0].total_fees
    assert vault.totalSupply() == amount + vault.balanceOf(accountant)
    assert vault.totalAssets() == amount

    price_per_share = vault.price_per_share() / 10 ** vault.decimals()
    assert price_per_share < 1.0
    assert price_per_share > 0.99

    # Fish redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, [], sender=fish)

    assert vault.total_debt() == 0
    assert vault.totalSupply() == vault.balanceOf(accountant)
    assert asset.balanceOf(vault) == vault.convertToAssets(vault.balanceOf(accountant))

    assert asset.balanceOf(fish) < fish_amount
    assert asset.balanceOf(fish) > fish_amount - first_loss

    # Accountant redeems shares
    vault.redeem(
        vault.balanceOf(accountant), accountant, accountant, [], sender=accountant
    )

    assert vault.total_debt() == 0
    assert vault.totalSupply() == 0
    assert vault.totalAssets() == 0
    assert asset.balanceOf(vault) == 0

    assert (
        asset.balanceOf(accountant) + asset.balanceOf(fish)
        == 2 * fish_amount - first_loss
    )


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
