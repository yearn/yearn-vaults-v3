import ape
import pytest
from ape import chain
from utils import actions
from utils.constants import YEAR


def test_vault_airdrop_do_not_increase(gov, asset, vault):
    vault_balance = asset.balanceOf(vault)
    assert vault_balance != 0
    # vault.
    # aidrop to vault
    price_per_share = vault.pricePerShare()
    actions.airdrop_asset(gov, asset, vault, int(vault_balance / 10))
    assert vault.pricePerShare() == price_per_share
