import ape
import pytest
from ape import chain


def test_vault_airdrop_do_not_increase(
    gov, asset, vault, mint_and_deposit_into_vault, airdrop_asset
):
    mint_and_deposit_into_vault(vault, gov)
    vault_balance = asset.balanceOf(vault)
    assert vault_balance != 0
    # vault.
    # aidrop to vault
    price_per_share = vault.pricePerShare()
    airdrop_asset(gov, asset, vault, int(vault_balance / 10))
    assert vault.pricePerShare() == price_per_share


def test_vault_airdrop_do_not_increase_report_records_it(
    gov, asset, vault, mint_and_deposit_into_vault, airdrop_asset
):
    mint_and_deposit_into_vault(vault, gov)
    vault_balance = asset.balanceOf(vault)
    assert vault_balance != 0
    # vault.
    # aidrop to vault
    price_per_share = vault.pricePerShare()

    to_airdrop = int(vault_balance / 10)
    airdrop_asset(gov, asset, vault, to_airdrop)

    assert vault.pricePerShare() == price_per_share
    assert vault.totalIdle() == vault_balance
    assert asset.balanceOf(vault) == vault_balance + to_airdrop

    tx = vault.process_report(vault.address, sender=gov)

    event = list(tx.decode_logs(vault.StrategyReported))[0]

    assert event.strategy == vault.address
    assert event.gain == to_airdrop
    assert event.loss == 0
    assert event.current_debt == vault_balance + to_airdrop
    assert event.total_fees == 0

    # Profit is locked
    assert vault.pricePerShare() == price_per_share
    assert vault.totalIdle() == vault_balance + to_airdrop
    assert asset.balanceOf(vault) == vault_balance + to_airdrop

    chain.pending_timestamp = chain.pending_timestamp + vault.profitMaxUnlockTime() - 1
    chain.mine(timestamp=chain.pending_timestamp)
