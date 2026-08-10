import ape
import pytest
from ape import chain
from eth_account import Account

from utils.constants import MAX_INT, ROLES, ZERO_ADDRESS


def _vault_with_shares_and_hook(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    owner,
    amount,
):
    vault = create_vault(asset)
    user_deposit(owner, vault, asset, amount)
    hook = deploy_hook()
    vault.set_transfer_hook(hook.address, sender=gov)
    return vault, hook


def _assert_transfer_observation(
    hook,
    caller,
    sender,
    receiver,
    shares,
    sender_balance,
    receiver_balance,
    allowance,
    count=1,
):
    assert hook.last_transfer_caller() == caller.address
    assert hook.last_transfer_sender() == sender.address
    assert hook.last_transfer_receiver() == receiver.address
    assert hook.last_transfer_shares() == shares
    assert hook.last_transfer_sender_balance() == sender_balance
    assert hook.last_transfer_receiver_balance() == receiver_balance
    assert hook.last_transfer_allowance() == allowance
    assert hook.post_transfer_count() == count


def test_transfer_hook_reuses_withdraw_role_and_default_governance_role(
    asset, create_vault, vault_factory, gov
):
    vault = create_vault(asset)

    assert ROLES.WITHDRAW_LIMIT_MANAGER == 512
    assert ROLES.ALL == 16383
    assert vault.roles(gov.address) == ROLES.ALL
    assert ROLES.WITHDRAW_LIMIT_MANAGER in ROLES(vault.roles(gov.address))
    assert vault.apiVersion() == "3.1.1"
    assert vault_factory.apiVersion() == "3.1.1"


def test_set_transfer_hook_acl_event_replace_and_clear(
    asset, create_vault, deploy_hook, gov, bunny
):
    vault = create_vault(asset)
    first_hook = deploy_hook()
    second_hook = deploy_hook()

    assert vault.transfer_hook() == ZERO_ADDRESS

    with ape.reverts("not allowed"):
        vault.set_transfer_hook(first_hook.address, sender=bunny)

    vault.set_role(bunny.address, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)
    with ape.reverts("not allowed"):
        vault.set_transfer_hook(first_hook.address, sender=bunny)

    vault.set_role(bunny.address, ROLES.WITHDRAW_LIMIT_MANAGER, sender=gov)

    for new_hook in (first_hook.address, second_hook.address, ZERO_ADDRESS):
        tx = vault.set_transfer_hook(new_hook, sender=bunny)
        events = list(tx.decode_logs(vault.UpdateTransferHook))

        assert len(events) == 1
        assert events[0].transfer_hook == new_hook
        assert vault.transfer_hook() == new_hook


def test_transfer_hook_is_mutable_and_active_while_paused(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 4
    vault = create_vault(asset)
    user_deposit(fish, vault, asset, amount * 2)
    first_hook = deploy_hook()
    second_hook = deploy_hook()
    flow_hook = deploy_hook()

    vault.setPaused(True, sender=gov)
    vault.set_transfer_hook(first_hook.address, sender=gov)
    vault.set_deposit_hook(flow_hook.address, sender=gov)
    vault.set_withdraw_hook(flow_hook.address, sender=gov)

    with ape.reverts("exceed deposit limit"):
        vault.deposit(amount, fish.address, sender=fish)
    with ape.reverts("exceed deposit limit"):
        vault.mint(amount, fish.address, sender=fish)
    with ape.reverts("paused"):
        vault.withdraw(amount, fish.address, fish.address, sender=fish)
    with ape.reverts("paused"):
        vault.redeem(amount, fish.address, fish.address, sender=fish)

    assert flow_hook.post_deposit_count() == 0
    assert flow_hook.post_withdraw_count() == 0

    vault.transfer(bunny.address, amount, sender=fish)
    assert first_hook.post_transfer_count() == 1

    vault.set_transfer_hook(second_hook.address, sender=gov)
    vault.approve(bunny.address, amount, sender=fish)
    vault.transferFrom(fish.address, doggie.address, amount, sender=bunny)

    assert first_hook.post_transfer_count() == 1
    assert second_hook.post_transfer_count() == 1

    vault.set_transfer_hook(ZERO_ADDRESS, sender=gov)
    assert vault.transfer_hook() == ZERO_ADDRESS


def test_transfer_hook_is_mutable_and_active_during_shutdown(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 3
    vault, first_hook = _vault_with_shares_and_hook(
        asset, create_vault, deploy_hook, user_deposit, gov, fish, amount * 2
    )
    second_hook = deploy_hook()

    vault.set_role(bunny.address, ROLES.EMERGENCY_MANAGER, sender=gov)
    vault.shutdown_vault(sender=bunny)

    assert vault.transfer_hook() == first_hook.address
    vault.transfer(doggie.address, amount, sender=fish)
    assert first_hook.post_transfer_count() == 1

    with ape.reverts("not allowed"):
        vault.set_transfer_hook(ZERO_ADDRESS, sender=bunny)

    vault.set_transfer_hook(second_hook.address, sender=gov)
    assert vault.transfer_hook() == second_hook.address
    vault.transfer(bunny.address, amount, sender=fish)
    assert second_hook.post_transfer_count() == 1
    vault.set_transfer_hook(ZERO_ADDRESS, sender=gov)
    assert vault.transfer_hook() == ZERO_ADDRESS


def test_direct_transfer_calls_hook_after_state_and_transfer_log(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    fish_amount,
):
    amount = fish_amount // 3
    vault, hook = _vault_with_shares_and_hook(
        asset, create_vault, deploy_hook, user_deposit, gov, fish, amount * 2
    )
    total_supply = vault.totalSupply()

    tx = vault.transfer(bunny.address, amount, sender=fish)

    transfer_log = list(tx.decode_logs(vault.Transfer))[0]
    hook_log = list(tx.decode_logs(hook.TransferHookCalled))[0]
    assert transfer_log.log_index < hook_log.log_index
    _assert_transfer_observation(
        hook,
        fish,
        fish,
        bunny,
        amount,
        amount,
        amount,
        0,
    )
    assert vault.totalSupply() == total_supply


def test_direct_transfer_hook_revert_rolls_back_state(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    fish_amount,
):
    amount = fish_amount // 2
    vault, hook = _vault_with_shares_and_hook(
        asset, create_vault, deploy_hook, user_deposit, gov, fish, amount
    )
    hook.set_revert_post_transfer(True, sender=gov)
    total_supply = vault.totalSupply()

    with ape.reverts("post transfer revert"):
        vault.transfer(bunny.address, amount, sender=fish)

    assert vault.balanceOf(fish.address) == amount
    assert vault.balanceOf(bunny.address) == 0
    assert vault.totalSupply() == total_supply
    assert hook.post_transfer_count() == 0


def test_transfer_from_calls_hook_after_finite_allowance_is_spent(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 3
    allowance = amount * 2
    vault, hook = _vault_with_shares_and_hook(
        asset, create_vault, deploy_hook, user_deposit, gov, fish, allowance
    )
    vault.approve(bunny.address, allowance, sender=fish)

    tx = vault.transferFrom(fish.address, doggie.address, amount, sender=bunny)

    approval_log = list(tx.decode_logs(vault.Approval))[0]
    transfer_log = list(tx.decode_logs(vault.Transfer))[0]
    hook_log = list(tx.decode_logs(hook.TransferHookCalled))[0]
    assert approval_log.log_index < transfer_log.log_index < hook_log.log_index
    _assert_transfer_observation(
        hook,
        bunny,
        fish,
        doggie,
        amount,
        amount,
        amount,
        amount,
    )


def test_transfer_from_preserves_infinite_allowance(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 4
    vault, hook = _vault_with_shares_and_hook(
        asset, create_vault, deploy_hook, user_deposit, gov, fish, amount
    )
    vault.approve(bunny.address, MAX_INT, sender=fish)

    tx = vault.transferFrom(fish.address, doggie.address, amount, sender=bunny)

    assert list(tx.decode_logs(vault.Approval)) == []
    assert vault.allowance(fish.address, bunny.address) == MAX_INT
    _assert_transfer_observation(
        hook,
        bunny,
        fish,
        doggie,
        amount,
        0,
        amount,
        MAX_INT,
    )


def test_transfer_from_hook_revert_restores_allowance_and_balances(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 2
    vault, hook = _vault_with_shares_and_hook(
        asset, create_vault, deploy_hook, user_deposit, gov, fish, amount
    )
    vault.approve(bunny.address, amount, sender=fish)
    hook.set_revert_post_transfer(True, sender=gov)
    total_supply = vault.totalSupply()

    with ape.reverts("post transfer revert"):
        vault.transferFrom(fish.address, doggie.address, amount, sender=bunny)

    assert vault.balanceOf(fish.address) == amount
    assert vault.balanceOf(doggie.address) == 0
    assert vault.allowance(fish.address, bunny.address) == amount
    assert vault.totalSupply() == total_supply
    assert hook.post_transfer_count() == 0


def test_zero_value_transfers_call_hook(
    asset, create_vault, deploy_hook, gov, fish, bunny, doggie
):
    vault = create_vault(asset)
    hook = deploy_hook()
    vault.set_transfer_hook(hook.address, sender=gov)

    vault.transfer(doggie.address, 0, sender=fish)
    _assert_transfer_observation(hook, fish, fish, doggie, 0, 0, 0, 0)

    # A zero-value delegated transfer needs no allowance or shares. Even the nominal
    # sender may be the zero address, so every callback address is attacker-controlled.
    vault.transferFrom(ZERO_ADDRESS, bunny.address, 0, sender=doggie)
    assert hook.last_transfer_caller() == doggie.address
    assert hook.last_transfer_sender() == ZERO_ADDRESS
    assert hook.last_transfer_receiver() == bunny.address
    assert hook.last_transfer_shares() == 0
    assert hook.last_transfer_allowance() == 0
    assert hook.post_transfer_count() == 2


def test_self_transfers_call_hook_and_preserve_balance(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    fish_amount,
):
    amount = fish_amount // 4
    balance = amount * 2
    vault, hook = _vault_with_shares_and_hook(
        asset, create_vault, deploy_hook, user_deposit, gov, fish, balance
    )

    vault.transfer(fish.address, amount, sender=fish)
    _assert_transfer_observation(
        hook, fish, fish, fish, amount, balance, balance, 0
    )

    vault.approve(bunny.address, amount, sender=fish)
    vault.transferFrom(fish.address, fish.address, amount, sender=bunny)
    _assert_transfer_observation(
        hook, bunny, fish, fish, amount, balance, balance, 0, count=2
    )
    assert vault.balanceOf(fish.address) == balance
    assert vault.allowance(fish.address, bunny.address) == 0


def test_rejected_transfers_never_call_hook(
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 4
    vault, hook = _vault_with_shares_and_hook(
        asset, create_vault, deploy_hook, user_deposit, gov, fish, amount
    )

    with ape.reverts():
        vault.transfer(ZERO_ADDRESS, amount, sender=fish)
    with ape.reverts():
        vault.transfer(vault.address, amount, sender=fish)
    with ape.reverts("insufficient funds"):
        vault.transfer(doggie.address, amount + 1, sender=fish)
    with ape.reverts("insufficient allowance"):
        vault.transferFrom(fish.address, doggie.address, amount, sender=bunny)

    vault.approve(bunny.address, amount + 1, sender=fish)
    with ape.reverts("insufficient funds"):
        vault.transferFrom(fish.address, doggie.address, amount + 1, sender=bunny)

    assert hook.post_transfer_count() == 0
    assert vault.balanceOf(fish.address) == amount
    assert vault.balanceOf(doggie.address) == 0


def test_permit_then_transfer_from_reports_spender_as_caller(
    asset,
    create_vault,
    deploy_hook,
    sign_vault_permit,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 5
    owner = Account.create()
    vault = create_vault(asset)
    hook = deploy_hook()
    asset.approve(vault.address, amount, sender=fish)
    vault.deposit(amount, owner.address, sender=fish)
    vault.set_transfer_hook(hook.address, sender=gov)

    deadline = chain.pending_timestamp + 3600
    signature = sign_vault_permit(
        vault,
        owner,
        str(bunny.address),
        allowance=amount,
        deadline=deadline,
    )
    stale_signature = sign_vault_permit(
        vault,
        owner,
        str(bunny.address),
        allowance=amount,
        deadline=deadline,
        override_version="3.1.0",
    )

    with ape.reverts("invalid signature"):
        vault.permit(
            owner.address,
            bunny.address,
            amount,
            deadline,
            stale_signature.v,
            stale_signature.r.to_bytes(32, byteorder="big"),
            stale_signature.s.to_bytes(32, byteorder="big"),
            sender=bunny,
        )

    assert vault.nonces(owner.address) == 0
    vault.permit(
        owner.address,
        bunny.address,
        amount,
        deadline,
        signature.v,
        signature.r.to_bytes(32, byteorder="big"),
        signature.s.to_bytes(32, byteorder="big"),
        sender=bunny,
    )

    vault.transferFrom(owner.address, doggie.address, amount, sender=bunny)

    assert hook.last_transfer_caller() == bunny.address
    assert hook.last_transfer_sender() == owner.address
    assert hook.last_transfer_receiver() == doggie.address
    assert hook.last_transfer_shares() == amount
    assert hook.last_transfer_allowance() == 0


def test_erc4626_issue_and_burn_paths_do_not_call_transfer_hook(
    asset,
    create_vault,
    deploy_hook,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 8
    vault = create_vault(asset)
    hook = deploy_hook()
    vault.set_transfer_hook(hook.address, sender=gov)
    asset.mint(fish.address, amount * 2, sender=gov)
    asset.approve(vault.address, amount * 2, sender=fish)

    vault.deposit(amount, bunny.address, sender=fish)
    vault.mint(amount, bunny.address, sender=fish)
    vault.withdraw(amount, doggie.address, bunny.address, sender=bunny)
    vault.redeem(amount, doggie.address, bunny.address, sender=bunny)

    assert hook.post_transfer_count() == 0
    assert vault.balanceOf(bunny.address) == 0
    assert vault.totalSupply() == 0


def test_report_fee_and_profit_lock_shares_do_not_call_transfer_hook(
    asset,
    create_vault,
    create_strategy,
    deploy_hook,
    deploy_accountant,
    set_fees_for_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    airdrop_asset,
    gov,
    fish,
    fish_amount,
):
    amount = fish_amount // 10
    gain = amount // 2
    vault = create_vault(asset)
    strategy = create_strategy(vault)
    accountant = deploy_accountant(vault)
    hook = deploy_hook()

    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    set_fees_for_strategy(gov, strategy, accountant, 0, 5_000)
    vault.set_transfer_hook(hook.address, sender=gov)

    airdrop_asset(gov, asset, strategy, gain)
    strategy.report(sender=gov)
    vault.process_report(strategy.address, sender=gov)

    assert vault.balanceOf(accountant.address) > 0
    assert vault.balanceOf(vault.address) > 0
    assert hook.post_transfer_count() == 0

    vault.setProfitMaxUnlockTime(0, sender=gov)
    assert hook.post_transfer_count() == 0


@pytest.mark.parametrize("reentry_mode", [1, 2, 3])
def test_post_transfer_same_vault_reentry_reverts_atomically(
    reentry_mode,
    asset,
    create_vault,
    deploy_hook,
    user_deposit,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 4
    vault, hook = _vault_with_shares_and_hook(
        asset, create_vault, deploy_hook, user_deposit, gov, fish, amount * 2
    )
    vault.approve(hook.address, amount, sender=fish)
    hook.set_post_transfer_reentry(
        reentry_mode,
        fish.address,
        doggie.address,
        1,
        sender=gov,
    )

    with ape.reverts():
        vault.transfer(hook.address, amount, sender=fish)

    assert vault.balanceOf(fish.address) == amount * 2
    assert vault.balanceOf(hook.address) == 0
    assert vault.balanceOf(doggie.address) == 0
    assert vault.allowance(fish.address, hook.address) == amount
    assert hook.post_transfer_count() == 0


def test_shared_lock_blocks_transfer_from_deposit_hook_when_transfer_hook_unset(
    asset,
    create_vault,
    deploy_hook,
    gov,
    fish,
    bunny,
    fish_amount,
):
    amount = fish_amount // 4
    vault = create_vault(asset)
    deposit_hook = deploy_hook()
    vault.set_deposit_hook(deposit_hook.address, sender=gov)
    deposit_hook.set_reenter_post_deposit(True, bunny.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=fish)
    fish_asset_balance = asset.balanceOf(fish.address)

    assert vault.transfer_hook() == ZERO_ADDRESS
    with ape.reverts():
        vault.deposit(amount, deposit_hook.address, sender=fish)

    assert deposit_hook.post_deposit_count() == 0
    assert vault.balanceOf(deposit_hook.address) == 0
    assert vault.balanceOf(bunny.address) == 0
    assert vault.totalSupply() == 0
    assert asset.balanceOf(fish.address) == fish_asset_balance


def test_eoa_hook_bricks_transfers_until_cleared(
    asset,
    create_vault,
    user_deposit,
    gov,
    fish,
    bunny,
    doggie,
    fish_amount,
):
    amount = fish_amount // 4
    vault = create_vault(asset)
    user_deposit(fish, vault, asset, amount)
    vault.set_transfer_hook(bunny.address, sender=gov)

    with ape.reverts():
        vault.transfer(doggie.address, amount, sender=fish)

    assert vault.balanceOf(fish.address) == amount
    assert vault.balanceOf(doggie.address) == 0

    vault.set_transfer_hook(ZERO_ADDRESS, sender=gov)
    vault.transfer(doggie.address, amount, sender=fish)
    assert vault.balanceOf(fish.address) == 0
    assert vault.balanceOf(doggie.address) == amount
