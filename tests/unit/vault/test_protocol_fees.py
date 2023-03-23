from ape import chain
import pytest
from utils.constants import ROLES, YEAR
from utils.utils import days_to_secs


def test__report_with_no_protocol_fees(
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

    assert vault_factory.protocol_fee_config().fee_bps == 0

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    assert vault.pricePerShare() == int(10 ** vault.decimals())
    # We increase time after profit has been released and check estimation
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].protocol_fees == 0

    shares_protocol = vault.balanceOf(gov.address)
    assert vault.convertToAssets(shares_protocol) == 0
    assert vault.pricePerShare() == int(10 ** vault.decimals())


def test__report_gain_with_protocol_fees__set_pre_vault_deploy(
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
    airdrop_asset,
):
    amount = fish_amount // 10
    profit = int(amount * 0.0025)
    vault_factory.set_protocol_fee_bps(25, sender=gov)
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    airdrop_asset(gov, asset, strategy, profit)

    price_per_share_pre = vault.pricePerShare()

    assert vault.pricePerShare() == int(10 ** vault.decimals())

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = vault.lastReport() + YEAR
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].protocol_fees == int(amount * 0.0025)

    shares_protocol = vault.balanceOf(gov.address)
    assert (
        pytest.approx(
            price_per_share_pre * shares_protocol // (10 ** vault.decimals()), rel=1e-6
        )
        == amount * 0.0025
    )
    assert vault.pricePerShare() == int(10 ** vault.decimals())


def test__report_no_gain_with_protocol_fees__set_pre_vault_deploy(
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

    vault_factory.set_protocol_fee_bps(25, sender=gov)
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    price_per_share_pre = vault.pricePerShare()

    assert vault.pricePerShare() == int(10 ** vault.decimals())

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = vault.lastReport() + YEAR
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert pytest.approx(event[0].protocol_fees, abs=100) == int(
        (amount / (amount + amount * 0.0025)) * (amount * 0.0025)
    )

    shares_protocol = vault.balanceOf(gov.address)
    assert (
        pytest.approx(
            price_per_share_pre * shares_protocol // (10 ** vault.decimals()), rel=1e-6
        )
        == amount * 0.0025
    )
    assert pytest.approx(
        vault.pricePerShare(), rel=1e-8
    ) == amount * 10 ** vault.decimals() // (amount + amount * 0.0025)


def test__report_gain_with_protocol_fees__set_post_vault_deploy(
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
    airdrop_asset,
):
    amount = fish_amount // 10
    profit = int(amount * 0.0025)
    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    airdrop_asset(gov, asset, strategy, profit)

    # Let some time pass
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)

    # We do changes in factory
    vault_factory.set_protocol_fee_bps(25, sender=gov)
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    assert vault.pricePerShare() == int(10 ** vault.decimals())

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = vault_factory.protocol_fee_config().fee_last_change + YEAR
    price_per_share_pre = vault.pricePerShare()
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].protocol_fees == int(amount * 0.0025)

    shares_protocol = vault.balanceOf(gov.address)
    assert (
        pytest.approx(
            price_per_share_pre * shares_protocol // (10 ** vault.decimals()), rel=1e-6
        )
        == amount * 0.0025
    )

    assert vault.pricePerShare() == int(10 ** vault.decimals())


def test__report_no_gain_with_protocol_fees__set_post_vault_deploy(
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

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    # Let some time pass
    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(10)

    # We do changes in factory
    vault_factory.set_protocol_fee_bps(25, sender=gov)
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    assert vault.pricePerShare() == int(10 ** vault.decimals())

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = vault_factory.protocol_fee_config().fee_last_change + YEAR
    price_per_share_pre = vault.pricePerShare()
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert pytest.approx(event[0].protocol_fees, abs=100) == int(
        (amount / (amount + amount * 0.0025)) * (amount * 0.0025)
    )

    shares_protocol = vault.balanceOf(gov.address)
    assert (
        pytest.approx(
            price_per_share_pre * shares_protocol // (10 ** vault.decimals()), rel=1e-6
        )
        == amount * 0.0025
    )

    assert pytest.approx(
        vault.pricePerShare(), rel=1e-8
    ) == amount * 10 ** vault.decimals() // (amount + amount * 0.0025)


def test__report_gain_several_times_in_a_day(
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
    airdrop_asset,
):
    amount = fish_amount // 10
    profit = int(amount * 0.0025)
    vault_factory.set_protocol_fee_bps(25, sender=gov)
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    airdrop_asset(gov, asset, strategy, profit)

    assert vault.pricePerShare() == int(10 ** vault.decimals())

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = vault.lastReport() + YEAR
    price_per_share_pre = vault.pricePerShare()
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].protocol_fees == int(amount * 0.0025)

    shares_protocol = vault.balanceOf(gov.address)
    assert (
        pytest.approx(
            price_per_share_pre * shares_protocol // (10 ** vault.decimals()), rel=1e-6
        )
        == amount * 0.0025
    )
    # we have enough profit to offset the fees so pps doesnt change
    assert vault.pricePerShare() == int(10 ** vault.decimals())

    # When a day has not passed, no new protocol fees are charged
    chain.pending_timestamp = vault.lastReport() + int(days_to_secs(0.75))
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].protocol_fees == 0

    airdrop_asset(gov, asset, strategy, profit)
    chain.pending_timestamp = vault.lastReport() + int(days_to_secs(1))
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert pytest.approx(event[0].protocol_fees, abs=1) == int(
        (amount + profit) * 0.0025 * (days_to_secs(1) / YEAR)
    )


def test__report_no_gain_several_times_in_a_day(
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

    vault_factory.set_protocol_fee_bps(25, sender=gov)
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    assert vault.pricePerShare() == int(10 ** vault.decimals())

    # We increase time after profit has been released and check estimation
    chain.pending_timestamp = vault.lastReport() + YEAR
    price_per_share_pre = vault.pricePerShare()
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    # with no gain the fees cause a loss and will be issued less than the expected amount
    assert pytest.approx(event[0].protocol_fees, abs=100) == int(
        (amount / (amount + amount * 0.0025)) * (amount * 0.0025)
    )

    shares_protocol = vault.balanceOf(gov.address)
    assert (
        pytest.approx(
            price_per_share_pre * shares_protocol // (10 ** vault.decimals()), rel=1e-6
        )
        == amount * 0.0025
    )
    assert pytest.approx(
        vault.pricePerShare(), rel=1e-8
    ) == amount * 10 ** vault.decimals() // (amount + amount * 0.0025)

    # When a day has not passed, no new protocol fees are charged
    chain.pending_timestamp = vault.lastReport() + int(days_to_secs(0.75))
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert event[0].protocol_fees == 0

    chain.pending_timestamp = vault.lastReport() + int(days_to_secs(1))
    tx = vault.process_report(strategy, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))
    assert pytest.approx(event[0].protocol_fees, abs=10) == int(
        amount
        / (amount + amount * 0.0025 * (days_to_secs(1) / YEAR))
        * (amount * 0.0025 * (days_to_secs(1) / YEAR))
    )
