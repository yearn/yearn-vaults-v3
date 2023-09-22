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
    gov, asset, vault, mint_and_deposit_into_vault, fish, fish_amount, create_strategy
):
    amount = fish_amount

    strategy = create_strategy(vault)

    mint_and_deposit_into_vault(vault, fish, amount)

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    with ape.reverts("not active"):
        vault.buy_debt(strategy, amount, sender=gov)


def test_buy_debt__no_debt__reverts(
    gov, asset, vault, mint_and_deposit_into_vault, fish_amount, create_strategy, fish
):
    amount = fish_amount

    strategy = create_strategy(vault)

    vault.add_strategy(strategy.address, sender=gov)

    mint_and_deposit_into_vault(vault, fish, amount)

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
    fish,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, fish, amount)

    add_debt_to_strategy(gov, strategy, vault, amount)

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    with ape.reverts("nothing to buy with"):
        vault.buy_debt(strategy, 0, sender=gov)


def test_buy_debt__more_than_available__withdraws_current_debt(
    gov,
    asset,
    vault,
    mint_and_deposit_into_vault,
    fish_amount,
    strategy,
    add_debt_to_strategy,
    fish,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, fish, amount)

    add_debt_to_strategy(gov, strategy, vault, amount)

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    before_balance = asset.balanceOf(gov)
    before_shares = strategy.balanceOf(gov)

    tx = vault.buy_debt(strategy, amount * 2, sender=gov)

    logs = list(tx.decode_logs(vault.DebtPurchased))[0]

    assert logs.strategy == strategy.address
    assert logs.amount == amount

    logs = list(tx.decode_logs(vault.DebtUpdated))

    assert len(logs) == 1
    assert logs[0].strategy == strategy.address
    assert logs[0].current_debt == amount
    assert logs[0].new_debt == 0

    assert vault.totalIdle() == amount
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** asset.decimals()
    assert vault.strategies(strategy)["current_debt"] == 0
    # assert shares got moved
    assert asset.balanceOf(gov) == before_balance - amount
    assert strategy.balanceOf(gov) == before_shares + amount


def test_buy_debt__full_debt(
    gov,
    asset,
    vault,
    mint_and_deposit_into_vault,
    fish_amount,
    strategy,
    add_debt_to_strategy,
    fish,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, fish, amount)

    add_debt_to_strategy(gov, strategy, vault, amount)

    # Approve vault to pull funds.
    asset.mint(gov.address, amount, sender=gov)
    asset.approve(vault.address, amount, sender=gov)

    before_balance = asset.balanceOf(gov)
    before_shares = strategy.balanceOf(gov)

    tx = vault.buy_debt(strategy, amount, sender=gov)

    logs = list(tx.decode_logs(vault.DebtPurchased))[0]

    assert logs.strategy == strategy.address
    assert logs.amount == amount

    logs = list(tx.decode_logs(vault.DebtUpdated))

    assert len(logs) == 1
    assert logs[0].strategy == strategy.address
    assert logs[0].current_debt == amount
    assert logs[0].new_debt == 0

    assert vault.totalIdle() == amount
    assert vault.totalDebt() == 0
    assert vault.pricePerShare() == 10 ** asset.decimals()
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
    fish,
):
    amount = fish_amount

    mint_and_deposit_into_vault(vault, fish, amount)

    add_debt_to_strategy(gov, strategy, vault, amount)

    to_buy = amount // 2

    # Approve vault to pull funds.
    asset.mint(gov.address, to_buy, sender=gov)
    asset.approve(vault.address, to_buy, sender=gov)

    before_balance = asset.balanceOf(gov)
    before_shares = strategy.balanceOf(gov)

    tx = vault.buy_debt(strategy, to_buy, sender=gov)

    logs = list(tx.decode_logs(vault.DebtPurchased))[0]

    assert logs.strategy == strategy.address
    assert logs.amount == to_buy

    logs = list(tx.decode_logs(vault.DebtUpdated))

    assert len(logs) == 1
    assert logs[0].strategy == strategy.address
    assert logs[0].current_debt == amount
    assert logs[0].new_debt == amount - to_buy

    assert vault.totalIdle() == to_buy
    assert vault.totalDebt() == amount - to_buy
    assert vault.pricePerShare() == 10 ** asset.decimals()
    assert vault.strategies(strategy)["current_debt"] == amount - to_buy
    # assert shares got moved
    assert asset.balanceOf(gov) == before_balance - to_buy
    assert strategy.balanceOf(gov) == before_shares + to_buy
