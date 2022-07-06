import ape
import pytest
from utils.constants import ZERO_ADDRESS


def test_deploy_fee_manager(project, gov):
    fee_manager = gov.deploy(project.FeeManager)

    assert fee_manager.feeManager() == gov


def test_distribute(gov, bunny, vault, fee_manager):
    with ape.reverts("not fee manager"):
        fee_manager.distribute(vault.address, sender=bunny)

    rewards = vault.balanceOf(gov)
    # give fee manager vault shares
    vault.transfer(fee_manager.address, rewards, sender=gov)
    assert vault.balanceOf(fee_manager) == rewards

    tx = fee_manager.distribute(vault.address, sender=gov)
    event = list(tx.decode_logs(fee_manager.DistributeRewards))

    assert len(event) == 1
    assert event[0].rewards == rewards

    assert vault.balanceOf(gov) == rewards


@pytest.mark.parametrize("performance_fee", [0, 2500, 5000])
def test_set_performance_fee__with_valid_performance_fee(
    gov, vault, fee_manager, performance_fee
):
    tx = fee_manager.setPerformanceFee(vault.address, performance_fee, sender=gov)
    event = list(tx.decode_logs(fee_manager.UpdatePerformanceFee))

    assert len(event) == 1
    assert event[0].performanceFee == performance_fee

    assert fee_manager.fees(vault).performanceFee == performance_fee


def test_set_performance_fee_with_invalid_performance_fee_reverts(
    gov, bunny, vault, fee_manager
):
    valid_performance_fee = 5000
    invalid_performance_fee = 5001

    with ape.reverts("not fee manager"):
        fee_manager.setPerformanceFee(
            vault.address, valid_performance_fee, sender=bunny
        )

    with ape.reverts("exceeds performance fee threshold"):
        fee_manager.setPerformanceFee(
            vault.address, invalid_performance_fee, sender=gov
        )


@pytest.mark.parametrize("management_fee", [0, 5000, 10000])
def test_management_fee__with_valid_management_fee(
    gov, vault, fee_manager, management_fee
):
    tx = fee_manager.setManagementFee(vault.address, management_fee, sender=gov)
    event = list(tx.decode_logs(fee_manager.UpdateManagementFee))

    assert len(event) == 1
    assert event[0].managementFee == management_fee

    assert fee_manager.fees(vault).managementFee == management_fee


def test_management_fee__with_invalid_management_fee_reverts(
    gov, bunny, vault, fee_manager
):
    valid_management_fee = 10000
    invalid_management_fee = 10001

    with ape.reverts("not fee manager"):
        fee_manager.setManagementFee(vault.address, valid_management_fee, sender=bunny)

    with ape.reverts("exceeds management fee threshold"):
        fee_manager.setManagementFee(vault.address, invalid_management_fee, sender=gov)


def test_commit_fee_manager__with_new_fee_manager(gov, bunny, fee_manager):
    with ape.reverts("not fee manager"):
        fee_manager.commitFeeManager(bunny.address, sender=bunny)

    tx = fee_manager.commitFeeManager(bunny.address, sender=gov)
    event = list(tx.decode_logs(fee_manager.CommitFeeManager))

    assert len(event) == 1
    assert event[0].feeManager == bunny.address

    assert fee_manager.futureFeeManager() == bunny.address


def test_apply_fee_manager__with_new_fee_manager(gov, bunny, fee_manager):
    fee_manager.commitFeeManager(ZERO_ADDRESS, sender=gov)

    with ape.reverts("not fee manager"):
        fee_manager.applyFeeManager(sender=bunny)

    with ape.reverts("future fee manager != zero address"):
        fee_manager.applyFeeManager(sender=gov)

    fee_manager.commitFeeManager(bunny.address, sender=gov)

    tx = fee_manager.applyFeeManager(sender=gov)
    event = list(tx.decode_logs(fee_manager.ApplyFeeManager))

    assert len(event) == 1
    assert event[0].feeManager == bunny.address

    assert fee_manager.feeManager() == bunny.address
