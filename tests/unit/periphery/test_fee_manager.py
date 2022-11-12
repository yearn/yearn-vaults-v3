import ape
import pytest
from utils.constants import ZERO_ADDRESS


def test_deploy_accountant(project, gov, asset):
    accountant = gov.deploy(project.Accountant, asset)

    assert accountant.fee_manager() == gov


def test_distribute(gov, bunny, vault, deploy_accountant):
    accountant = deploy_accountant(vault)
    with ape.reverts("not fee manager"):
        accountant.distribute(vault.address, sender=bunny)

    rewards = vault.balanceOf(gov)
    # give fee manager vault shares
    vault.transfer(accountant.address, rewards, sender=gov)
    assert vault.balanceOf(accountant) == rewards

    tx = accountant.distribute(vault.address, sender=gov)
    event = list(tx.decode_logs(accountant.DistributeRewards))

    assert len(event) == 1
    assert event[0].rewards == rewards

    assert vault.balanceOf(gov) == rewards


@pytest.mark.parametrize("performance_fee", [0, 2500, 5000])
def test_set_performance_fee__with_valid_performance_fee(
    gov, vault, deploy_accountant, performance_fee
):
    accountant = deploy_accountant(vault)
    tx = accountant.set_performance_fee(vault.address, performance_fee, sender=gov)
    event = list(tx.decode_logs(accountant.UpdatePerformanceFee))

    assert len(event) == 1
    assert event[0].performance_fee == performance_fee

    assert accountant.fees(vault).performance_fee == performance_fee


def test_set_performance_fee_with_invalid_performance_fee_reverts(
    gov, bunny, vault, deploy_accountant
):
    accountant = deploy_accountant(vault)
    valid_performance_fee = 5000
    invalid_performance_fee = 5001

    with ape.reverts("not fee manager"):
        accountant.set_performance_fee(
            vault.address, valid_performance_fee, sender=bunny
        )

    with ape.reverts("exceeds performance fee threshold"):
        accountant.set_performance_fee(
            vault.address, invalid_performance_fee, sender=gov
        )


@pytest.mark.parametrize("management_fee", [0, 5000, 10000])
def test_management_fee__with_valid_management_fee(
    gov, vault, deploy_accountant, management_fee
):
    accountant = deploy_accountant(vault)
    tx = accountant.set_management_fee(vault.address, management_fee, sender=gov)
    event = list(tx.decode_logs(accountant.UpdateManagementFee))

    assert len(event) == 1
    assert event[0].management_fee == management_fee

    assert accountant.fees(vault).management_fee == management_fee


def test_management_fee__with_invalid_management_fee_reverts(
    gov, bunny, vault, deploy_accountant
):
    accountant = deploy_accountant(vault)
    valid_management_fee = 10000
    invalid_management_fee = 10001

    with ape.reverts("not fee manager"):
        accountant.set_management_fee(vault.address, valid_management_fee, sender=bunny)

    with ape.reverts("exceeds management fee threshold"):
        accountant.set_management_fee(vault.address, invalid_management_fee, sender=gov)


def test_commit_fee_manager__with_new_fee_manager(gov, bunny, vault, deploy_accountant):
    accountant = deploy_accountant(vault)
    with ape.reverts("not fee manager"):
        accountant.commit_fee_manager(bunny.address, sender=bunny)

    tx = accountant.commit_fee_manager(bunny.address, sender=gov)
    event = list(tx.decode_logs(accountant.CommitFeeManager))

    assert len(event) == 1
    assert event[0].fee_manager == bunny.address

    assert accountant.future_fee_manager() == bunny.address


def test_apply_fee_manager__with_new_fee_manager(gov, bunny, vault, deploy_accountant):
    accountant = deploy_accountant(vault)
    accountant.commit_fee_manager(ZERO_ADDRESS, sender=gov)

    with ape.reverts("not fee manager"):
        accountant.apply_fee_manager(sender=bunny)

    with ape.reverts("future fee manager != zero address"):
        accountant.apply_fee_manager(sender=gov)

    accountant.commit_fee_manager(bunny.address, sender=gov)

    tx = accountant.apply_fee_manager(sender=gov)
    event = list(tx.decode_logs(accountant.ApplyFeeManager))

    assert len(event) == 1
    assert event[0].fee_manager == bunny.address

    assert accountant.fee_manager() == bunny.address


@pytest.mark.parametrize("refund_ratio", [0, 5_000, 10_000])
def test_set_refund_ratio(gov, vault, deploy_accountant, refund_ratio):
    accountant = deploy_accountant(vault)
    tx = accountant.set_refund_ratio(vault.address, refund_ratio, sender=gov)
    event = list(tx.decode_logs(accountant.UpdateRefundRatio))

    assert len(event) == 1
    assert event[0].refund_ratio == refund_ratio

    assert accountant.refund_ratios(vault) == refund_ratio
