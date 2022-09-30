import ape
import pytest
from utils.constants import ROLES


@pytest.fixture(autouse=True)
def set_role(vault, gov):
    vault.set_role(
        gov.address,
        ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.ACCOUNTING_MANAGER,
        sender=gov,
    )


def test_sweep__with_asset_token_and_no_dust__reverts(gov, asset, vault):
    with ape.reverts("no dust"):
        vault.sweep(asset.address, sender=gov)


def test_sweep__with_asset_token__withdraws_airdrop_only(
    gov,
    asset,
    vault,
    strategy,
    mint_and_deposit_into_vault,
    airdrop_asset,
    add_debt_to_strategy,
):
    vault_balance = 10**22
    debt = vault_balance // 10
    asset_airdrop = vault_balance // 10
    mint_and_deposit_into_vault(vault, gov, vault_balance)
    assert vault.totalAssets() == vault_balance

    # airdrop extra assets to vault (e.g. user accidentally sends to vault)
    airdrop_asset(gov, asset, vault, asset_airdrop)
    assert asset.balanceOf(vault) == (vault_balance + asset_airdrop)
    # vault balance doesn't change from airdrops
    assert vault.totalAssets() == vault_balance

    # add debt to strategy to check debt is accounted for
    add_debt_to_strategy(gov, strategy, vault, debt)

    gov_balance = asset.balanceOf(gov)
    tx = vault.sweep(asset.address, sender=gov)
    event = list(tx.decode_logs(vault.Sweep))

    assert len(event) == 1
    assert event[0].token == asset.address
    assert event[0].amount == asset_airdrop

    assert asset.balanceOf(gov) == asset_airdrop + gov_balance
    assert asset.balanceOf(vault) == (vault_balance - debt)
    assert vault.totalAssets() == vault_balance


def test_sweep__with_token__withdraws_token(
    gov,
    asset,
    vault,
    strategy,
    mint_and_deposit_into_vault,
    airdrop_asset,
    add_debt_to_strategy,
):
    # create vault with strategy and debt allocated
    vault_balance = 10**22
    debt = vault_balance // 10
    mock_token_airdrop = vault_balance // 10
    mint_and_deposit_into_vault(vault, gov, vault_balance)
    add_debt_to_strategy(gov, strategy, vault, debt)

    # airdrop random token to vault
    airdrop_asset(gov, asset, vault, mock_token_airdrop)

    gov_balance = asset.balanceOf(gov)
    tx = vault.sweep(asset.address, sender=gov)
    event = list(tx.decode_logs(vault.Sweep))

    assert len(event) == 1
    assert event[0].token == asset.address
    assert event[0].amount == mock_token_airdrop

    assert asset.balanceOf(gov) == mock_token_airdrop + gov_balance
    assert asset.balanceOf(vault) == vault_balance - debt
    assert vault.totalAssets() == vault_balance
