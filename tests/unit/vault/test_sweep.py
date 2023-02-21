import ape
import pytest
from utils.constants import ROLES


@pytest.fixture(autouse=True)
def set_role(vault, gov):
    vault.set_role(
        gov.address,
        ROLES.ADD_STRATEGY_MANAGER
        | ROLES.REVOKE_STRATEGY_MANAGER
        | ROLES.DEBT_MANAGER
        | ROLES.MAX_DEBT_MANAGER
        | ROLES.SWEEPER,
        sender=gov,
    )


def test_sweep__with_asset_token_and_no_dust__reverts(gov, asset, vault):
    with ape.reverts("no dust"):
        vault.sweep(asset.address, sender=gov)


def test_sweep__with_vault_token__reverts(gov, asset, vault):
    with ape.reverts("can't sweep self"):
        vault.sweep(vault.address, sender=gov)


def test_sweep__with_strategies_token__reverts(
    chain,
    gov,
    asset,
    vault,
    create_strategy,
    mint_and_deposit_into_vault,
    add_debt_to_strategy,
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy.address, sender=gov)

    mint_and_deposit_into_vault(vault)
    vault_balance = asset.balanceOf(vault)
    add_debt_to_strategy(gov, new_strategy, vault, vault_balance)

    with ape.reverts("can't sweep strategy"):
        vault.sweep(new_strategy, sender=gov)


def test_sweep__with_strategies_token__been_revoked__sweeps(
    chain,
    gov,
    asset,
    vault,
    create_strategy,
    mint_and_deposit_into_vault,
    add_debt_to_strategy,
    mint_and_deposit_into_strategy,
):
    new_strategy = create_strategy(vault)
    vault.add_strategy(new_strategy.address, sender=gov)

    mint_and_deposit_into_vault(vault)
    vault_balance = asset.balanceOf(vault)
    add_debt_to_strategy(gov, new_strategy, vault, vault_balance)

    with ape.reverts("can't sweep strategy"):
        vault.sweep(new_strategy, sender=gov)

    # remove debt and revoke strategy
    vault.update_debt(new_strategy, 0, sender=gov)
    vault.revoke_strategy(new_strategy, sender=gov)

    # mint some strategy shares
    mint_and_deposit_into_strategy(new_strategy, gov)

    shares = new_strategy.balanceOf(gov)

    # airdrop shares to the vault
    new_strategy.transfer(vault, shares, sender=gov)

    balance_before = new_strategy.balanceOf(gov)

    vault.sweep(new_strategy, sender=gov)

    assert new_strategy.balanceOf(gov) - balance_before == shares


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


def test_sweep__with_mock_token__withdraws_token(
    gov,
    mock_token,
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

    # give gov the amount of mock_token to airdrop
    mock_token.mint(gov, mock_token_airdrop, sender=gov)
    # airdrop mock token to vault
    airdrop_asset(gov, mock_token, vault, mock_token_airdrop)

    gov_balance = mock_token.balanceOf(gov)
    tx = vault.sweep(mock_token.address, sender=gov)
    event = list(tx.decode_logs(vault.Sweep))

    assert len(event) == 1
    assert event[0].token == mock_token.address
    assert event[0].amount == mock_token_airdrop

    assert mock_token.balanceOf(gov) == mock_token_airdrop + gov_balance
    assert mock_token.balanceOf(vault) == 0
    assert vault.totalAssets() == vault_balance
