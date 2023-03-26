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
