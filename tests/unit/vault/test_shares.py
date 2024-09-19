import ape
import pytest
from utils import checks
from utils.constants import MAX_INT, ZERO_ADDRESS, WEEK, ROLES


def test_deposit__with_invalid_recipient__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 1000

    with ape.reverts("exceed deposit limit"):
        vault.deposit(amount, vault.address, sender=fish)
    with ape.reverts("exceed deposit limit"):
        vault.deposit(amount, ZERO_ADDRESS, sender=fish)


def test_deposit__with_zero_funds__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("cannot deposit zero"):
        vault.deposit(amount, fish.address, sender=fish)


def test_deposit__with_deposit_limit_within_deposit_limit__deposit_balance(
    fish, fish_amount, asset, create_vault, user_deposit
):
    vault = create_vault(asset, deposit_limit=fish_amount)
    amount = fish_amount
    shares = amount

    tx = user_deposit(fish, vault, asset, amount)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    assert vault.totalIdle() == amount
    assert vault.balanceOf(fish) == amount
    assert vault.totalSupply() == amount
    assert asset.balanceOf(fish) == 0


def test_deposit__with_deposit_limit_exceed_deposit_limit__reverts(
    fish, fish_amount, asset, create_vault
):
    amount = fish_amount
    deposit_limit = amount - 1
    vault = create_vault(asset, deposit_limit=deposit_limit)

    with ape.reverts("exceed deposit limit"):
        vault.deposit(amount, fish.address, sender=fish)


def test_deposit_all__with_deposit_limit_exceed_deposit_limit__deposit_deposit_limit(
    fish, fish_amount, asset, create_vault
):
    amount = fish_amount
    deposit_limit = amount // 2
    vault = create_vault(asset, deposit_limit=deposit_limit)

    asset.approve(vault.address, amount, sender=fish)

    with ape.reverts("exceed deposit limit"):
        vault.deposit(MAX_INT, fish.address, sender=fish)


def test_deposit__with_delegation__deposits_to_delegate(
    fish, fish_amount, bunny, asset, create_vault
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check amount is non-zero
    assert amount > 0

    # delegate deposit to bunny
    asset.approve(vault.address, amount, sender=fish)
    tx = vault.deposit(amount, bunny.address, sender=fish)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].owner == bunny
    assert event[0].shares == shares
    assert event[0].assets == amount

    # fish has no more assets
    assert asset.balanceOf(fish) == 0
    # fish has no shares
    assert vault.balanceOf(fish) == 0
    # bunny has been issued vault shares
    assert vault.balanceOf(bunny) == shares


def test_mint__with_invalid_recipient__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    shares = 100

    with ape.reverts("exceed deposit limit"):
        vault.mint(shares, vault.address, sender=fish)
    with ape.reverts("exceed deposit limit"):
        vault.mint(shares, ZERO_ADDRESS, sender=fish)


def test_mint__with_zero_funds__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    shares = 0

    with ape.reverts("cannot deposit zero"):
        vault.mint(shares, fish.address, sender=fish)


def test_mint__with_deposit_limit_within_deposit_limit__deposit_balance(
    fish, fish_amount, asset, create_vault
):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount

    asset.approve(vault.address, amount, sender=fish)
    tx = vault.mint(shares, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    assert vault.totalIdle() == amount
    assert vault.balanceOf(fish) == amount
    assert vault.totalSupply() == amount
    assert asset.balanceOf(fish) == 0


def test_mint__with_deposit_limit_exceed_deposit_limit__reverts(
    fish, fish_amount, asset, create_vault
):
    amount = fish_amount
    shares = amount
    deposit_limit = amount - 1
    vault = create_vault(asset, deposit_limit=deposit_limit)

    with ape.reverts("exceed deposit limit"):
        vault.mint(shares, fish.address, sender=fish)


def test_mint__with_delegation__deposits_to_delegate(
    fish, fish_amount, bunny, asset, create_vault
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check amount is non-zero
    assert amount > 0

    # delegate mint to bunny
    asset.approve(vault.address, amount, sender=fish)
    tx = vault.mint(shares, bunny.address, sender=fish)
    event = list(tx.decode_logs(vault.Deposit))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].owner == bunny
    assert event[0].shares == shares
    assert event[0].assets == amount

    # fish has no more assets
    assert asset.balanceOf(fish) == 0
    # fish has no shares
    assert vault.balanceOf(fish) == 0
    # bunny has been issued vault shares
    assert vault.balanceOf(bunny) == shares


def test_withdraw(fish, fish_amount, asset, create_vault, user_deposit):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount

    user_deposit(fish, vault, asset, amount)

    tx = vault.withdraw(shares, fish.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__with_insufficient_shares__reverts(
    fish, fish_amount, asset, create_vault, user_deposit
):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount + 1

    user_deposit(fish, vault, asset, amount)

    with ape.reverts("insufficient shares to redeem"):
        vault.withdraw(shares, fish.address, fish.address, sender=fish)


def test_withdraw__with_no_shares__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    shares = 0

    with ape.reverts("no shares to redeem"):
        vault.withdraw(shares, fish.address, fish.address, sender=fish)


def test_withdraw__with_delegation__withdraws_to_delegate(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # withdraw to bunny
    tx = vault.withdraw(shares, bunny.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == bunny
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    # fish no longer has shares
    assert vault.balanceOf(fish) == 0
    # fish did not receive tokens
    assert asset.balanceOf(fish) == 0
    # bunny has tokens
    assert asset.balanceOf(bunny) == amount


def test_withdraw__with_delegation_and_sufficient_allowance__withdraws(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # check initial allowance is zero
    assert vault.allowance(fish, bunny) == 0

    # withdraw as bunny to fish
    vault.approve(bunny.address, amount, sender=fish)
    tx = vault.withdraw(shares, fish.address, fish.address, sender=bunny)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == bunny
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert vault.allowance(fish, bunny) == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == amount


def test_withdraw__with_delegation_and_insufficient_allowance__reverts(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # withdraw as bunny to fish
    with ape.reverts("insufficient allowance"):
        vault.withdraw(shares, fish.address, fish.address, sender=bunny)


def test_redeem(fish, fish_amount, asset, create_vault, user_deposit):
    vault = create_vault(asset)
    amount = fish_amount
    shares = amount

    user_deposit(fish, vault, asset, amount)

    tx = vault.redeem(amount, fish.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == amount


def test_redeem__with_insufficient_shares__reverts(
    fish, fish_amount, asset, create_vault, user_deposit
):
    vault = create_vault(asset)
    amount = fish_amount
    redemption_amount = amount + 1

    user_deposit(fish, vault, asset, amount)

    with ape.reverts("insufficient shares to redeem"):
        vault.redeem(redemption_amount, fish.address, fish.address, sender=fish)


def test_redeem__with_no_shares__reverts(fish, asset, create_vault):
    vault = create_vault(asset)
    amount = 0

    with ape.reverts("no shares to redeem"):
        vault.withdraw(amount, fish.address, fish.address, sender=fish)


def test_redeem__with_delegation__withdraws_to_delegate(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # redeem to bunny
    tx = vault.redeem(amount, bunny.address, fish.address, sender=fish)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == fish
    assert event[0].receiver == bunny
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    # fish no longer has shares
    assert vault.balanceOf(fish) == 0
    # fish did not receive tokens
    assert asset.balanceOf(fish) == 0
    # bunny has tokens
    assert asset.balanceOf(bunny) == amount


def test_redeem__with_delegation_and_sufficient_allowance__withdraws(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    shares = amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # check initial allowance is zero
    assert vault.allowance(fish, bunny) == 0

    # withdraw as bunny to fish
    vault.approve(bunny.address, amount, sender=fish)
    tx = vault.redeem(amount, fish.address, fish.address, sender=bunny)
    event = list(tx.decode_logs(vault.Withdraw))

    assert len(event) == 1
    assert event[0].sender == bunny
    assert event[0].receiver == fish
    assert event[0].owner == fish
    assert event[0].shares == shares
    assert event[0].assets == amount

    checks.check_vault_empty(vault)
    assert vault.allowance(fish, bunny) == 0
    assert asset.balanceOf(vault) == 0
    assert asset.balanceOf(fish) == amount


def test_redeem__with_delegation_and_insufficient_allowance__reverts(
    fish, fish_amount, bunny, asset, create_vault, user_deposit
):
    amount = fish_amount
    vault = create_vault(asset)

    # check balance is non-zero
    assert amount > 0

    # deposit balance
    user_deposit(fish, vault, asset, amount)

    # withdraw as bunny to fish
    with ape.reverts("insufficient allowance"):
        vault.redeem(amount, fish.address, fish.address, sender=bunny)


@pytest.mark.parametrize("deposit_limit", [0, 10**18, MAX_INT])
def test_set_deposit_limit__with_deposit_limit(
    project, create_vault, gov, asset, deposit_limit
):
    vault = create_vault(
        asset=asset,
        governance=gov,
        max_profit_locking_time=WEEK,
        vault_name="VaultV3",
        vault_symbol="AV",
    )
    vault.set_role(gov, ROLES.DEPOSIT_LIMIT_MANAGER, sender=gov)
    tx = vault.set_deposit_limit(deposit_limit, sender=gov)
    event = list(tx.decode_logs(vault.UpdateDepositLimit))

    assert event[0].deposit_limit == deposit_limit
    assert vault.deposit_limit() == deposit_limit


def create_profit(
    asset,
    strategy,
    gov,
    vault,
    profit,
    total_fees=0,
    total_refunds=0,
    by_pass_fees=False,
):
    # We create a virtual profit
    initial_debt = vault.strategies(strategy).current_debt
    asset.transfer(strategy, profit, sender=gov)
    strategy.report(sender=gov)
    tx = vault.process_report(strategy, sender=gov)
    event = list(tx.decode_logs(vault.StrategyReported))

    return event[0].total_fees


def test__deposit_shares_with_zero_total_supply_positive_assets(
    asset, fish_amount, fish, initial_set_up, gov
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10

    vault, strategy, _ = initial_set_up(asset, gov, amount, fish)
    create_profit(asset, strategy, gov, vault, first_profit)
    vault.update_debt(strategy, int(0), sender=gov)
    assert (
        vault.totalSupply() > amount
    )  # there are more shares than deposits (due to profit unlock)

    # User redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, sender=fish)

    assert vault.totalSupply() > 0

    ape.chain.mine(timestamp=ape.chain.pending_timestamp + 14 * 24 * 3600)

    assert vault.totalSupply() == 0

    vault.deposit(amount, fish, sender=fish)

    # shares should be minted at 1:1
    assert vault.balanceOf(fish) == amount
    assert vault.pricePerShare() > (10 ** vault.decimals())


def test__mint_shares_with_zero_total_supply_positive_assets(
    asset, fish_amount, fish, initial_set_up, gov
):
    amount = fish_amount // 10
    first_profit = fish_amount // 10

    vault, strategy, _ = initial_set_up(asset, gov, amount, fish)
    create_profit(asset, strategy, gov, vault, first_profit)
    vault.update_debt(strategy, int(0), sender=gov)
    assert (
        vault.totalSupply() > amount
    )  # there are more shares than deposits (due to profit unlock)

    # User redeems shares
    vault.redeem(vault.balanceOf(fish), fish, fish, sender=fish)

    assert vault.totalSupply() > 0

    ape.chain.mine(timestamp=ape.chain.pending_timestamp + 14 * 24 * 3600)

    assert vault.totalSupply() == 0

    vault.mint(amount, fish, sender=fish)

    # shares should be minted at 1:1
    assert vault.balanceOf(fish) == amount
    assert vault.pricePerShare() > (10 ** vault.decimals())


def test__deposit_with_zero_total_assets_positive_supply(
    asset, fish_amount, fish, initial_set_up, gov
):
    amount = fish_amount // 10

    vault, strategy, _ = initial_set_up(asset, gov, amount, fish)

    # Create a loss
    asset.transfer(gov, amount, sender=strategy)
    strategy.report(sender=gov)

    assert strategy.convertToAssets(amount) == 0

    vault.process_report(strategy, sender=gov)

    assert vault.totalAssets() == 0
    assert vault.totalSupply() != 0

    with ape.reverts("cannot mint zero"):
        vault.deposit(amount, fish, sender=fish)

    # shares should not be minted
    assert vault.balanceOf(fish) == amount
    assert vault.pricePerShare() == 0
    assert vault.convertToShares(amount) == 0
    assert vault.convertToAssets(amount) == 0
    # assert vault.maxDeposit(fish) == 0


def test__mint_with_zero_total_assets_positive_supply(
    asset, fish_amount, fish, initial_set_up, gov
):
    amount = fish_amount // 10

    vault, strategy, _ = initial_set_up(asset, gov, amount, fish)

    # Create a loss
    asset.transfer(gov, amount, sender=strategy)
    strategy.report(sender=gov)

    assert strategy.convertToAssets(amount) == 0

    vault.process_report(strategy, sender=gov)

    assert vault.totalAssets() == 0
    assert vault.totalSupply() != 0

    with ape.reverts("cannot deposit zero"):
        vault.mint(amount, fish, sender=fish)

    # shares should not be minted
    assert vault.balanceOf(fish) == amount
    assert vault.pricePerShare() == 0
    assert vault.convertToShares(amount) == 0
    assert vault.convertToAssets(amount) == 0
    # assert vault.maxMint(fish) == 0
