import ape
import pytest
from utils.constants import YEAR, DAY, ROLES, MAX_BPS_ACCOUNTANT, WEEK, MAX_INT
from utils.utils import days_to_secs


@pytest.fixture(autouse=True)
def seed_vault_with_funds(mint_and_deposit_into_vault, vault, gov):
    mint_and_deposit_into_vault(vault, gov, 10**18, 10**18 // 2)


@pytest.fixture(autouse=True)
def set_role(vault, gov):
    vault.set_role(
        gov.address,
        ROLES.EMERGENCY_MANAGER
        | ROLES.ADD_STRATEGY_MANAGER
        | ROLES.REVOKE_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.DEPOSIT_LIMIT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.ACCOUNTANT_MANAGER
        | ROLES.REPORTING_MANAGER,
        sender=gov,
    )


def test_process_report__with_inactive_strategy__reverts(gov, vault, create_strategy):
    strategy = create_strategy(vault)

    with ape.reverts("inactive strategy"):
        vault.process_report(strategy.address, sender=gov)


def test_process_report__with_gain_and_zero_fees(
    chain, gov, asset, vault, strategy, airdrop_asset, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2

    # add debt to strategy
    add_debt_to_strategy(gov, strategy, vault, new_debt)
    airdrop_asset(gov, asset, strategy, gain)
    # record gain
    strategy.report(sender=gov)

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.current_debt

    snapshot = chain.pending_timestamp
    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].current_debt == initial_debt + gain
    assert event[0].total_fees == 0

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.current_debt == initial_debt + gain
    assert vault.strategies(strategy.address).last_report == pytest.approx(
        snapshot, abs=1
    )


def test_process_report__with_gain_and_zero_management_fees(
    chain,
    gov,
    asset,
    vault,
    strategy,
    deploy_accountant,
    airdrop_asset,
    set_fees_for_strategy,
    add_debt_to_strategy,
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2
    management_fee = 0
    performance_fee = 5_000
    total_fee = gain // 2

    accountant = deploy_accountant(vault)
    # add debt to strategy
    add_debt_to_strategy(gov, strategy, vault, new_debt)
    # airdrop gain to strategy
    airdrop_asset(gov, asset, strategy, gain)
    # record gain
    strategy.report(sender=gov)
    # set up accountant
    set_fees_for_strategy(gov, strategy, accountant, management_fee, performance_fee)

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.current_debt

    snapshot = chain.pending_timestamp
    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].current_debt == initial_debt + gain
    assert event[0].total_fees == total_fee

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.current_debt == initial_debt + gain
    assert vault.strategies(strategy.address).last_report == pytest.approx(
        snapshot, abs=1
    )

    chain.pending_timestamp = chain.pending_timestamp + days_to_secs(14)
    # chain.mine(timestamp=chain.pending_timestamp)
    # Vault mints shares worth the fees to the accountant
    accountant_balance = vault.balanceOf(accountant)
    assert (
        pytest.approx(vault.convertToAssets(accountant_balance), rel=1e-5) == total_fee
    )


def test_process_report__with_gain_and_zero_performance_fees(
    chain,
    gov,
    asset,
    vault,
    strategy,
    deploy_accountant,
    airdrop_asset,
    set_fees_for_strategy,
    add_debt_to_strategy,
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2
    management_fee = 1000
    performance_fee = 0
    total_fee = vault_balance // 10  # 10% mgmt fee over all assets, over a year

    initial_total_assets = vault.totalAssets()
    initial_total_supply = vault.totalSupply()

    accountant = deploy_accountant(vault)
    # add debt to strategy
    add_debt_to_strategy(gov, strategy, vault, new_debt)
    # airdrop gain to strategy
    airdrop_asset(gov, asset, strategy, gain)
    # record gain
    strategy.report(sender=gov)
    # set up accountant
    set_fees_for_strategy(gov, strategy, accountant, management_fee, performance_fee)

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.current_debt

    chain.pending_timestamp += YEAR
    snapshot = chain.pending_timestamp
    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].current_debt == initial_debt + gain
    assert event[0].total_fees == pytest.approx(total_fee, rel=1e-4)

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.current_debt == initial_debt + gain
    assert vault.strategies(strategy.address).last_report == pytest.approx(
        snapshot, abs=1
    )

    # Vault mints shares worth the fees to the accountant
    accountant_balance = vault.balanceOf(accountant)
    assert (
        pytest.approx(vault.convertToAssets(accountant_balance), rel=1e-5) == total_fee
    )


def test_process_report__with_gain_and_both_fees(
    chain,
    gov,
    asset,
    vault,
    strategy,
    deploy_accountant,
    airdrop_asset,
    set_fees_for_strategy,
    add_debt_to_strategy,
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2
    management_fee = 2500
    performance_fee = 2500
    total_fee = gain // 4

    initial_total_assets = vault.totalAssets()
    initial_total_supply = vault.totalSupply()

    accountant = deploy_accountant(vault)
    # add debt to strategy
    add_debt_to_strategy(gov, strategy, vault, new_debt)
    # airdrop gain to strategy
    airdrop_asset(gov, asset, strategy, gain)
    # record gain
    strategy.report(sender=gov)
    # set up accountant
    set_fees_for_strategy(gov, strategy, accountant, management_fee, performance_fee)

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.current_debt

    snapshot = chain.pending_timestamp
    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].current_debt == initial_debt + gain
    assert event[0].total_fees == pytest.approx(total_fee, rel=1e-4)

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.current_debt == initial_debt + gain
    assert vault.strategies(strategy.address).last_report == pytest.approx(
        snapshot, abs=1
    )

    # Vault mints shares worth the fees to the accountant
    accountant_balance = vault.balanceOf(accountant)
    assert (
        pytest.approx(vault.convertToAssets(accountant_balance), rel=1e-5) == total_fee
    )


def test_process_report__with_fees_exceeding_fee_cap(
    chain,
    gov,
    asset,
    vault,
    strategy,
    deploy_accountant,
    airdrop_asset,
    set_fees_for_strategy,
    add_debt_to_strategy,
):
    # test that fees are capped to 75% of gains
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    gain = new_debt // 2
    management_fee = 5000
    performance_fee = 5000
    max_fee = gain * 3 // 4  # max fee set at 3/4

    accountant = deploy_accountant(vault)
    # add debt to strategy
    add_debt_to_strategy(gov, strategy, vault, new_debt)
    # airdrop gain to strategy
    airdrop_asset(gov, asset, strategy, gain)
    # record gain
    strategy.report(sender=gov)
    # set up accountant
    set_fees_for_strategy(gov, strategy, accountant, management_fee, performance_fee)

    strategy_params = vault.strategies(strategy.address)
    initial_debt = strategy_params.current_debt

    chain.pending_timestamp += YEAR  # need time to pass to accrue more fees
    snapshot = chain.pending_timestamp
    tx = vault.process_report(strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].current_debt == initial_debt + gain
    assert event[0].total_fees == max_fee

    strategy_params = vault.strategies(strategy.address)
    assert strategy_params.current_debt == initial_debt + gain
    assert vault.strategies(strategy.address).last_report == pytest.approx(
        snapshot, abs=1
    )

    # Vault mints shares worth the fees to the accountant
    accountant_balance = vault.balanceOf(accountant)
    assert pytest.approx(vault.convertToAssets(accountant_balance), rel=1e-5) == max_fee


def test_process_report__with_loss(
    chain, gov, asset, vault, lossy_strategy, add_debt_to_strategy
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    loss = new_debt // 2

    # add debt to strategy and incur loss
    add_debt_to_strategy(gov, lossy_strategy, vault, new_debt)
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    strategy_params = vault.strategies(lossy_strategy.address)
    initial_debt = strategy_params.current_debt

    snapshot = chain.pending_timestamp
    tx = vault.process_report(lossy_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].gain == 0
    assert event[0].loss == loss
    assert event[0].current_debt == initial_debt - loss
    assert event[0].total_fees == 0

    strategy_params = vault.strategies(lossy_strategy.address)
    assert strategy_params.current_debt == initial_debt - loss
    assert vault.strategies(lossy_strategy.address).last_report == pytest.approx(
        snapshot, abs=1
    )
    assert vault.pricePerShare() / 10 ** vault.decimals() == 0.5


def test_process_report__with_loss_and_management_fees(
    chain,
    gov,
    asset,
    vault,
    lossy_strategy,
    add_debt_to_strategy,
    set_fees_for_strategy,
    deploy_accountant,
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    loss = new_debt // 2
    management_fee = 1000
    performance_fee = 0
    refund_ratio = 0

    accountant = deploy_accountant(vault)
    # set up accountant
    set_fees_for_strategy(
        gov, lossy_strategy, accountant, management_fee, performance_fee, refund_ratio
    )

    # add debt to strategy and incur loss
    add_debt_to_strategy(gov, lossy_strategy, vault, new_debt)
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    strategy_params = vault.strategies(lossy_strategy.address)
    initial_debt = strategy_params.current_debt

    # Management fees relay on duration of invest, so we need to advance in time to see results
    initial_timestamp = chain.pending_timestamp
    initial_pps = vault.pricePerShare()
    chain.mine(timestamp=initial_timestamp + YEAR)
    initial_total_assets = vault.totalAssets()

    expected_management_fees = vault_balance // 10

    # with a loss we will not get the full expected fee
    expected_management_fees = (
        (initial_total_assets - loss)
        / (initial_total_assets + expected_management_fees)
        * expected_management_fees
    )

    snapshot = chain.pending_timestamp

    tx = vault.process_report(lossy_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].gain == 0
    assert event[0].loss == loss
    assert event[0].current_debt == initial_debt - loss
    assert event[0].total_fees == pytest.approx(expected_management_fees, rel=1e-5)

    strategy_params = vault.strategies(lossy_strategy.address)

    assert strategy_params.current_debt == initial_debt - loss
    assert vault.strategies(lossy_strategy.address).last_report == pytest.approx(
        snapshot, abs=1
    )
    assert vault.convertToAssets(vault.balanceOf(accountant)) == pytest.approx(
        expected_management_fees, rel=1e-5
    )

    # Without fees, pps would be 0.5, as loss is half of debt, but with fees pps should be even lower
    assert vault.pricePerShare() / 10 ** vault.decimals() < initial_pps / 2
    assert vault.totalAssets() == pytest.approx(initial_total_assets - loss, 1e-5)


def test_process_report__with_loss_and_refunds(
    chain,
    gov,
    asset,
    vault,
    lossy_strategy,
    add_debt_to_strategy,
    set_fees_for_strategy,
    deploy_accountant,
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    loss = new_debt // 2
    management_fee = 0
    performance_fee = 0
    refund_ratio = 10_000

    accountant = deploy_accountant(vault)
    # set up accountant
    asset.mint(accountant, loss, sender=gov)

    set_fees_for_strategy(
        gov, lossy_strategy, accountant, management_fee, performance_fee, refund_ratio
    )

    # add debt to strategy and incur loss
    add_debt_to_strategy(gov, lossy_strategy, vault, new_debt)
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    strategy_params = vault.strategies(lossy_strategy.address)
    initial_debt = strategy_params.current_debt

    pps_before_loss = vault.pricePerShare()
    assets_before_loss = vault.totalAssets()
    supply_before_loss = vault.totalSupply()
    tx = vault.process_report(lossy_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].gain == 0
    assert event[0].loss == loss
    assert event[0].current_debt == initial_debt - loss
    assert event[0].total_fees == 0
    assert event[0].total_refunds == loss

    # Due to refunds, pps should be the same as before the loss
    assert vault.pricePerShare() == pps_before_loss
    assert vault.totalAssets() == assets_before_loss
    assert vault.totalSupply() == supply_before_loss
    assert vault.totalDebt() == new_debt - loss
    assert vault.totalIdle() == loss


def test_process_report__with_loss_management_fees_and_refunds(
    chain,
    gov,
    asset,
    vault,
    create_lossy_strategy,
    add_debt_to_strategy,
    set_fees_for_strategy,
    deploy_accountant,
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    loss = new_debt // 2
    management_fee = 10_000
    performance_fee = 0
    refund_ratio = 10_000

    lossy_strategy = create_lossy_strategy(vault)
    vault.add_strategy(lossy_strategy.address, sender=gov)
    initial_timestamp = chain.pending_timestamp
    lossy_strategy.setMaxDebt(MAX_INT, sender=gov)
    accountant = deploy_accountant(vault)
    # set up accountant
    asset.mint(accountant, loss, sender=gov)

    set_fees_for_strategy(
        gov, lossy_strategy, accountant, management_fee, performance_fee, refund_ratio
    )

    # add debt to strategy and incur loss
    add_debt_to_strategy(gov, lossy_strategy, vault, new_debt)

    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    strategy_params = vault.strategies(lossy_strategy.address)
    initial_debt = strategy_params.current_debt
    pps_before_loss = vault.pricePerShare()
    assets_before_loss = vault.totalAssets()

    # let one day pass
    chain.pending_timestamp = initial_timestamp + DAY
    chain.mine(timestamp=chain.pending_timestamp)

    expected_management_fees = (
        new_debt
        * (chain.pending_timestamp - vault.strategies(lossy_strategy).last_report)
        * management_fee
        / MAX_BPS_ACCOUNTANT
        / YEAR
    )

    # with a loss we will not get the full expected fee
    expected_management_fees = (
        new_debt / (new_debt + expected_management_fees) * expected_management_fees
    )

    tx = vault.process_report(lossy_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].gain == 0
    assert event[0].loss == loss
    assert event[0].current_debt == initial_debt - loss
    assert event[0].total_fees == pytest.approx(expected_management_fees, 1e-4)
    assert event[0].total_refunds == loss

    # Due to fees, pps should be slightly below 1
    assert vault.pricePerShare() < pps_before_loss
    # Shares were minted at 1:1
    assert vault.convertToAssets(vault.balanceOf(accountant)) == pytest.approx(
        expected_management_fees, 1e-4
    )


def test_process_report__with_loss_and_refunds__not_enough_asset(
    chain,
    gov,
    asset,
    vault,
    lossy_strategy,
    add_debt_to_strategy,
    set_fees_for_strategy,
    deploy_accountant,
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    loss = new_debt // 2
    management_fee = 0
    performance_fee = 0
    refund_ratio = 10_000

    accountant = deploy_accountant(vault)
    # set up accountant with not enough funds
    actual_refund = loss // 2
    asset.mint(accountant, actual_refund, sender=gov)

    set_fees_for_strategy(
        gov, lossy_strategy, accountant, management_fee, performance_fee, refund_ratio
    )

    # add debt to strategy and incur loss
    add_debt_to_strategy(gov, lossy_strategy, vault, new_debt)
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    strategy_params = vault.strategies(lossy_strategy.address)
    initial_debt = strategy_params.current_debt

    pps_before_loss = vault.pricePerShare()
    assets_before_loss = vault.totalAssets()
    supply_before_loss = vault.totalSupply()
    tx = vault.process_report(lossy_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].gain == 0
    assert event[0].loss == loss
    assert event[0].current_debt == initial_debt - loss
    assert event[0].total_fees == 0
    assert event[0].total_refunds == actual_refund

    # Due to refunds, pps should be the same as before the loss
    assert vault.pricePerShare() < pps_before_loss
    assert vault.totalAssets() == assets_before_loss - (loss - actual_refund)
    assert vault.totalSupply() == supply_before_loss
    assert vault.totalDebt() == new_debt - loss
    assert vault.totalIdle() == actual_refund


def test_process_report__with_loss_and_refunds__not_enough_allowance(
    chain,
    gov,
    asset,
    vault,
    lossy_strategy,
    add_debt_to_strategy,
    set_fees_for_strategy,
    deploy_faulty_accountant,
):
    vault_balance = asset.balanceOf(vault)
    new_debt = vault_balance
    loss = new_debt // 2
    management_fee = 0
    performance_fee = 0
    refund_ratio = 10_000

    accountant = deploy_faulty_accountant(vault)
    # set up accountant with not enough funds
    actual_refund = loss // 2
    asset.mint(accountant, loss, sender=gov)

    set_fees_for_strategy(
        gov, lossy_strategy, accountant, management_fee, performance_fee, refund_ratio
    )

    # add debt to strategy and incur loss
    add_debt_to_strategy(gov, lossy_strategy, vault, new_debt)
    lossy_strategy.setLoss(gov.address, loss, sender=gov)

    strategy_params = vault.strategies(lossy_strategy.address)
    initial_debt = strategy_params.current_debt

    # Set approval below the intended refunds
    asset.approve(vault.address, actual_refund, sender=accountant)

    pps_before_loss = vault.pricePerShare()
    assets_before_loss = vault.totalAssets()
    supply_before_loss = vault.totalSupply()
    tx = vault.process_report(lossy_strategy.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == lossy_strategy.address
    assert event[0].gain == 0
    assert event[0].loss == loss
    assert event[0].current_debt == initial_debt - loss
    assert event[0].total_fees == 0
    assert event[0].total_refunds == actual_refund

    # Due to refunds, pps should be the same as before the loss
    assert vault.pricePerShare() < pps_before_loss
    assert vault.totalAssets() == assets_before_loss - (loss - actual_refund)
    assert vault.totalSupply() == supply_before_loss
    assert vault.totalDebt() == new_debt - loss
    assert vault.totalIdle() == actual_refund


def test_set_accountant__with_accountant(gov, vault, deploy_accountant):
    accountant = deploy_accountant(vault)
    tx = vault.set_accountant(accountant.address, sender=gov)
    event = list(tx.decode_logs(vault.UpdateAccountant))

    assert len(event) == 1
    assert event[0].accountant == accountant.address

    assert vault.accountant() == accountant.address


def test_process_report_on_self__gain_and_refunds(
    chain,
    gov,
    asset,
    vault,
    set_fees_for_strategy,
    airdrop_asset,
    deploy_flexible_accountant,
):
    vault_balance = asset.balanceOf(vault)
    gain = vault_balance // 10
    loss = 0
    management_fee = 0
    performance_fee = 0
    refund_ratio = 5_000
    refund = gain * refund_ratio // MAX_BPS_ACCOUNTANT

    accountant = deploy_flexible_accountant(vault)
    # set up accountant
    asset.mint(accountant, gain, sender=gov)

    set_fees_for_strategy(
        gov, vault, accountant, management_fee, performance_fee, refund_ratio
    )

    initial_idle = vault.totalIdle()

    airdrop_asset(gov, asset, vault, gain)

    # Not yet recorded
    assert vault.totalIdle() == initial_idle
    assert asset.balanceOf(vault) == initial_idle + gain
    pps_before = vault.pricePerShare()
    assets_before = vault.totalAssets()
    supply_before = vault.totalSupply()
    tx = vault.process_report(vault.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == vault.address
    assert event[0].gain == gain
    assert event[0].loss == 0
    assert event[0].current_debt == vault_balance + gain + refund
    assert event[0].total_fees == 0
    assert event[0].total_refunds == refund

    # Due to refunds, pps should have increased
    assert vault.pricePerShare() == pps_before
    assert vault.totalAssets() == vault_balance + gain + refund
    assert vault.totalSupply() > supply_before
    assert vault.totalDebt() == 0
    assert vault.totalIdle() == vault_balance + gain + refund
    assert asset.balanceOf(vault) == vault_balance + gain + refund

    chain.pending_timestamp += DAY
    chain.mine(timestamp=chain.pending_timestamp)

    assert vault.pricePerShare() > pps_before


def test_process_report_on_self__loss_and_refunds(
    chain,
    gov,
    asset,
    vault,
    set_fees_for_strategy,
    airdrop_asset,
    deploy_flexible_accountant,
):
    vault_balance = asset.balanceOf(vault)
    gain = 0
    loss = vault_balance // 10
    management_fee = 0
    performance_fee = 0
    refund_ratio = 5_000
    refund = loss * refund_ratio // MAX_BPS_ACCOUNTANT

    accountant = deploy_flexible_accountant(vault)
    # set up accountant
    asset.mint(accountant, loss, sender=gov)

    set_fees_for_strategy(
        gov, vault, accountant, management_fee, performance_fee, refund_ratio
    )

    initial_idle = vault.totalIdle()

    asset.transfer(gov, loss, sender=vault.address)

    # Not yet recorded
    assert vault.totalIdle() == initial_idle
    assert asset.balanceOf(vault) == initial_idle - loss
    pps_before = vault.pricePerShare()
    assets_before = vault.totalAssets()
    supply_before = vault.totalSupply()
    tx = vault.process_report(vault.address, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    assert len(event) == 1
    assert event[0].strategy == vault.address
    assert event[0].gain == gain
    assert event[0].loss == loss
    assert event[0].current_debt == vault_balance + refund - loss
    assert event[0].total_fees == 0
    assert event[0].total_refunds == refund

    # Due to refunds, pps should have increased
    assert vault.pricePerShare() < pps_before
    assert vault.totalAssets() == vault_balance + refund - loss
    assert vault.totalSupply() == supply_before
    assert vault.totalDebt() == 0
    assert vault.totalIdle() == vault_balance + refund - loss
    assert asset.balanceOf(vault) == vault_balance + refund - loss
