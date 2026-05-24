import ape
from utils.constants import MAX_INT, ROLES


def test_setPaused__no_emergency_manager__reverts(asset, create_vault, bunny):
    vault = create_vault(asset)

    with ape.reverts("not allowed"):
        vault.setPaused(True, sender=bunny)


def test_setPaused__emergency_manager(asset, create_vault, gov, bunny):
    vault = create_vault(asset)
    vault.set_role(bunny.address, ROLES.EMERGENCY_MANAGER, sender=gov)

    assert vault.isPaused() == False

    tx = vault.setPaused(True, sender=bunny)
    event = list(tx.decode_logs(vault.UpdatePaused))

    assert len(event) == 1
    assert event[0].paused == True
    assert vault.isPaused() == True

    tx = vault.setPaused(False, sender=bunny)
    event = list(tx.decode_logs(vault.UpdatePaused))

    assert len(event) == 1
    assert event[0].paused == False
    assert vault.isPaused() == False


def test_paused_blocks_erc4626_user_flows(
    asset, create_vault, fish, fish_amount, gov, mint_and_deposit_into_vault
):
    vault = create_vault(asset)
    amount = fish_amount

    mint_and_deposit_into_vault(vault, fish, amount)
    vault.setPaused(True, sender=gov)

    assert vault.maxDeposit(fish.address) == 0
    assert vault.maxMint(fish.address) == 0
    assert vault.maxWithdraw(fish.address) == 0
    assert vault.maxRedeem(fish.address) == 0

    with ape.reverts("exceed deposit limit"):
        vault.deposit(amount, fish.address, sender=fish)

    with ape.reverts("exceed deposit limit"):
        vault.mint(amount, fish.address, sender=fish)

    with ape.reverts("paused"):
        vault.withdraw(amount, fish.address, fish.address, sender=fish)

    with ape.reverts("paused"):
        vault.redeem(amount, fish.address, fish.address, sender=fish)


def test_unpause_restores_erc4626_user_flows(
    asset, create_vault, fish, fish_amount, gov
):
    vault = create_vault(asset)
    amount = fish_amount

    vault.setPaused(True, sender=gov)
    vault.setPaused(False, sender=gov)

    asset.mint(fish.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=fish)
    vault.deposit(amount, fish.address, sender=fish)

    assert vault.maxWithdraw(fish.address) == amount

    vault.withdraw(amount, fish.address, fish.address, sender=fish)
    assert vault.balanceOf(fish.address) == 0


def test_paused_keeps_erc20_share_flows_live(
    asset, create_vault, fish, fish_amount, bunny, gov, mint_and_deposit_into_vault
):
    vault = create_vault(asset)
    amount = fish_amount
    half = amount // 2

    mint_and_deposit_into_vault(vault, fish, amount)
    vault.setPaused(True, sender=gov)

    vault.transfer(bunny.address, half, sender=fish)
    vault.approve(bunny.address, half, sender=fish)
    vault.transferFrom(fish.address, bunny.address, half, sender=bunny)

    assert vault.balanceOf(fish.address) == 0
    assert vault.balanceOf(bunny.address) == amount


def test_paused_keeps_debt_management_live(
    asset, create_vault, create_strategy, gov, mint_and_deposit_into_vault
):
    vault = create_vault(asset)
    strategy = create_strategy(vault)
    amount = 10**18

    vault.add_strategy(strategy.address, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    mint_and_deposit_into_vault(vault, gov, amount)

    vault.setPaused(True, sender=gov)

    vault.update_max_debt_for_strategy(strategy.address, amount, sender=gov)
    vault.update_debt(strategy.address, amount, sender=gov)

    assert vault.strategies(strategy.address).current_debt == amount
    assert asset.balanceOf(strategy.address) == amount
