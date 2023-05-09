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
        | ROLES.DEBT_PURCHASER,
        sender=gov,
    )


def test_buy_debt__strategy_not_active__reverts(
    gov, asset, vault, mint_and_deposit_into_vault, fish_amount, create_strategy
):
    amount = fish_amount

    strategy = create_strategy(vault)

    mint_and_deposit_into_vault(vault)

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    with ape.reverts("not active"):
        vault.buy_debt(strategy, amount, sender=gov)


def test_buy_debt__no_debt__reverts(
    gov, asset, vault, mint_and_deposit_into_vault, fish_amount, create_strategy
):
    amount = fish_amount

    strategy = create_strategy(vault)

    vault.add_strategy(strategy.address, sender=gov)

    mint_and_deposit_into_vault(vault)

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    with ape.reverts("nothing to buy"):
        vault.buy_debt(strategy, amount, sender=gov)


def test_buy_debt__no_amount__reverts(
    gov,
    asset,
    vault,
    mint_and_deposit_into_vault,
    fish_amount,
    strategy,
    add_debt_to_strategy,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, gov, amount)

    add_debt_to_strategy(gov, strategy, vault, amount)

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    with ape.reverts("nothing to buy with"):
        vault.buy_debt(strategy, 0, sender=gov)


"""
def test_buy_debt__share_are_zero__reverts(gov, asset, vault, mint_and_deposit_into_vault, fish_amount, lossy_strategy, add_debt_to_strategy):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, gov, amount)

    add_debt_to_strategy(gov, lossy_strategy, vault, amount)

    # simulate a full loss so convertToShares() returns 0
    lossy_strategy.setLoss(gov, amount, sender=gov)

    #assert lossy_strategy.convertToShares(amount) == 0

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    with ape.reverts("can't buy 0"):
        vault.buy_debt(lossy_strategy, amount, sender=gov)
"""


def test_buy_debt__to_many_shares__reverts(
    gov,
    asset,
    vault,
    mint_and_deposit_into_vault,
    fish_amount,
    strategy,
    add_debt_to_strategy,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, gov, amount)

    add_debt_to_strategy(gov, strategy, vault, amount)

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    with ape.reverts("not enough shares"):
        vault.buy_debt(strategy, amount * 2, sender=gov)


def test_buy_debt__full_debt(
    gov,
    asset,
    vault,
    mint_and_deposit_into_vault,
    fish_amount,
    strategy,
    add_debt_to_strategy,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, gov, amount)

    add_debt_to_strategy(gov, strategy, vault, amount)

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    before_balance = asset.balanceOf(gov)
    before_shares = strategy.balanceOf(gov)

    vault.buy_debt(strategy, amount, sender=gov)

    assert vault.totalIdle() == amount
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** asset.decimals()
    # Should have revoked the strategy
    assert vault.strategies(strategy)["activation"] == 0
    assert vault.strategies(strategy)["last_report"] == 0
    assert vault.strategies(strategy)["max_debt"] == 0
    assert vault.strategies(strategy)["current_debt"] == 0
    # assert shares got moved
    assert asset.balanceOf(gov) == before_balance - amount
    assert strategy.balanceOf(gov) == before_shares + amount


def test_buy_debt__half_debt(
    gov,
    asset,
    vault,
    mint_and_deposit_into_vault,
    fish_amount,
    strategy,
    add_debt_to_strategy,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, gov, amount)

    add_debt_to_strategy(gov, strategy, vault, amount)

    to_buy = amount // 2

    # Approve vault to pull funds.
    asset.mint(gov.address, to_buy, sender=gov)
    asset.approve(vault.address, to_buy, sender=gov)

    before_balance = asset.balanceOf(gov)
    before_shares = strategy.balanceOf(gov)

    vault.buy_debt(strategy, to_buy, sender=gov)

    assert vault.totalIdle() == to_buy
    assert vault.totalDebt() == amount - to_buy
    assert vault.pricePerShare() == 10 ** asset.decimals()
    # Should have revoked the strategy
    assert vault.strategies(strategy)["activation"] != 0
    assert vault.strategies(strategy)["last_report"] != 0
    assert vault.strategies(strategy)["max_debt"] != 0
    assert vault.strategies(strategy)["current_debt"] == amount - to_buy
    # assert shares got moved
    assert asset.balanceOf(gov) == before_balance - to_buy
    assert strategy.balanceOf(gov) == before_shares + to_buy
