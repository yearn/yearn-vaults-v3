import ape
import pytest
from utils.constants import MAX_BPS, ZERO_ADDRESS

INVALID_RATIO = MAX_BPS + 1
DEFAULT_PROFIT_LIMIT_RATIO = 100
DEFAULT_LOSS_LIMIT_RATIO = 1


def test_deploy_health_check(project, gov):
    health_check = gov.deploy(project.CommonHealthCheck)

    assert health_check.healthCheckManager() == gov.address


def test_check__with_gain_passing_health_check__returns_true(
    gov, strategy, health_check
):
    profit_limit = 1_000
    loss_limit = 0
    current_debt = 10**18
    gain = current_debt * profit_limit // MAX_BPS
    loss = 0

    health_check.setStrategyLimits(
        strategy.address, profit_limit, loss_limit, sender=gov
    )

    assert (
        health_check.check(strategy.address, gain, loss, current_debt, sender=gov)
        == True
    )


def test_check__with_gain_failing_health_check__returns_false(
    gov, strategy, health_check
):
    profit_limit = 1_000
    loss_limit = 0
    current_debt = 10**18
    gain = current_debt * profit_limit // MAX_BPS + 1
    loss = 0

    health_check.setStrategyLimits(
        strategy.address, profit_limit, loss_limit, sender=gov
    )

    assert (
        health_check.check(strategy.address, gain, loss, current_debt, sender=gov)
        == False
    )


def test_check__with_gain_passing_default_health_check__returns_true(
    gov, strategy, health_check
):
    current_debt = 10**18
    gain = current_debt * DEFAULT_PROFIT_LIMIT_RATIO // MAX_BPS
    loss = 0

    assert (
        health_check.check(strategy.address, gain, loss, current_debt, sender=gov)
        == True
    )


def test_check__with_gain_failing_default_health_check__returns_false(
    gov, strategy, health_check
):
    current_debt = 10**18
    gain = current_debt * DEFAULT_PROFIT_LIMIT_RATIO // MAX_BPS + 1
    loss = 0

    assert (
        health_check.check(strategy.address, gain, loss, current_debt, sender=gov)
        == False
    )


def test_check__with_loss_passing_health_check__returns_true(
    gov, strategy, health_check
):
    profit_limit = 0
    loss_limit = 1_000
    current_debt = 10**18
    gain = 0
    loss = current_debt * loss_limit // MAX_BPS

    health_check.setStrategyLimits(
        strategy.address, profit_limit, loss_limit, sender=gov
    )

    assert (
        health_check.check(strategy.address, gain, loss, current_debt, sender=gov)
        == True
    )


def test_check__with_loss_failing_health_check__returns_false(
    gov, strategy, health_check
):
    profit_limit = 0
    loss_limit = 1_000
    current_debt = 10**18
    gain = 0
    loss = current_debt * loss_limit // MAX_BPS + 1

    health_check.setStrategyLimits(
        strategy.address, profit_limit, loss_limit, sender=gov
    )

    assert (
        health_check.check(strategy.address, gain, loss, current_debt, sender=gov)
        == False
    )


def test_check__with_loss_passing_default_health_check__returns_true(
    gov, strategy, health_check
):
    current_debt = 10**18
    gain = 0
    loss = current_debt * DEFAULT_LOSS_LIMIT_RATIO // MAX_BPS

    assert (
        health_check.check(strategy.address, gain, loss, current_debt, sender=gov)
        == True
    )


def test_check__with_loss_failing_default_health_check__returns_false(
    gov, strategy, health_check
):
    current_debt = 10**18
    gain = 0
    loss = current_debt * DEFAULT_LOSS_LIMIT_RATIO // MAX_BPS + 1

    assert (
        health_check.check(strategy.address, gain, loss, current_debt, sender=gov)
        == False
    )


def test_set_disabled_health_check_state__without_permissions__reverts(
    bunny, strategy, health_check
):
    is_disabled = True

    with ape.reverts("not health check manager"):
        health_check.setDisabledHealthCheckState(strategy, is_disabled, sender=bunny)


@pytest.mark.parametrize("is_disabled", [True, False])
def test_set_disabled_health_check_state__with_permissions__sets_disabled_health_check(
    gov, strategy, health_check, is_disabled
):
    tx = health_check.setDisabledHealthCheckState(strategy, is_disabled, sender=gov)
    event = list(tx.decode_logs(health_check.DisableHealthCheckStatusUpdated))

    assert len(event) == 1
    assert event[0].strategy == strategy.address
    assert event[0].isDisabled == is_disabled

    assert health_check.disabledHealthChecks(strategy.address) == is_disabled


def test_set_default_profit_limit_ratio__without_permissions__reverts(
    bunny, health_check
):
    with ape.reverts("not health check manager"):
        health_check.setDefaultProfitLimitRatio(0, sender=bunny)


def test_set_default_profit_limit_ratio__with_invalid_profit_limit_ratio__reverts(
    gov, health_check
):
    with ape.reverts("profit limit ratio out of bounds"):
        health_check.setDefaultProfitLimitRatio(INVALID_RATIO, sender=gov)


@pytest.mark.parametrize("profit_limit_ratio", [0, 9_999])
def test_set_default_profit_limit_ratio__with_valid_profit_limit_ratio__sets_profit_limit_ratio(
    gov, health_check, profit_limit_ratio
):
    health_check.setDefaultProfitLimitRatio(profit_limit_ratio, sender=gov)


def test_set_default_loss_limit_ratio__without_permissions__reverts(
    bunny, health_check
):
    with ape.reverts("not health check manager"):
        health_check.setDefaultLossLimitRatio(0, sender=bunny)


def test_set_default_loss_limit_ratio__with_invalid_loss_limit_ratio__reverts(
    gov, health_check
):
    with ape.reverts("loss limit ratio out of bounds"):
        health_check.setDefaultLossLimitRatio(INVALID_RATIO, sender=gov)


@pytest.mark.parametrize("loss_limit_ratio", [0, 9_999])
def test_set_default_loss_limit_ratio__with_valid_loss_limit_ratio__sets_loss_limit_ratio(
    gov, health_check, loss_limit_ratio
):
    health_check.setDefaultLossLimitRatio(loss_limit_ratio, sender=gov)


def test_set_strategy_limit__without_permissions__reverts(
    bunny, strategy, health_check
):
    with ape.reverts("not health check manager"):
        health_check.setStrategyLimits(strategy.address, 0, 0, sender=bunny)


def test_set_strategy_limit__with_invalid_limit_ratios__reverts(
    gov, strategy, health_check
):
    with ape.reverts("profit limit ratio out of bounds"):
        health_check.setStrategyLimits(strategy.address, INVALID_RATIO, 0, sender=gov)
    with ape.reverts("loss limit ratio out of bounds"):
        health_check.setStrategyLimits(strategy.address, 0, INVALID_RATIO, sender=gov)


@pytest.mark.parametrize("profit_limit_ratio", [0, 9_999])
@pytest.mark.parametrize("loss_limit_ratio", [0, 9_999])
def test_set_strategy_limit__with_valid_limit_ratios__sets_limits(
    gov, strategy, health_check, profit_limit_ratio, loss_limit_ratio
):
    health_check.setStrategyLimits(
        strategy.address, profit_limit_ratio, loss_limit_ratio, sender=gov
    )

    strategy_limit = health_check.strategyLimits(strategy.address)
    assert strategy_limit.profitLimitRatio == profit_limit_ratio
    assert strategy_limit.lossLimitRatio == loss_limit_ratio
    assert strategy_limit.active == True


def test_commit_health_check_manager__with_new_health_check_manager(
    gov, bunny, health_check
):
    with ape.reverts("not health check manager"):
        health_check.commitHealthCheckManager(bunny.address, sender=bunny)

    tx = health_check.commitHealthCheckManager(bunny.address, sender=gov)
    event = list(tx.decode_logs(health_check.CommitHealthCheckManager))

    assert len(event) == 1
    assert event[0].healthCheckManager == bunny.address

    assert health_check.futureHealthCheckManager() == bunny.address


def test_apply_health_check_manager__with_new_health_check_manager(
    gov, bunny, health_check
):
    health_check.commitHealthCheckManager(ZERO_ADDRESS, sender=gov)

    with ape.reverts("not health check manager"):
        health_check.applyHealthCheckManager(sender=bunny)

    with ape.reverts("future health check manager != zero address"):
        health_check.applyHealthCheckManager(sender=gov)

    health_check.commitHealthCheckManager(bunny.address, sender=gov)

    tx = health_check.applyHealthCheckManager(sender=gov)
    event = list(tx.decode_logs(health_check.ApplyHealthCheckManager))

    assert len(event) == 1
    assert event[0].healthCheckManager == bunny.address

    assert health_check.healthCheckManager() == bunny.address
