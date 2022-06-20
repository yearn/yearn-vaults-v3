from ape import chain
from utils import actions


# placeholder tests for test mocks
def test_liquid_strategy__with_fee(gov, vault, create_strategy):
    strategy = create_strategy(vault)
    fee = 500 # 5%

    strategy.setFee(fee, sender=gov)

    assert strategy.fee() == fee


def test_locked_strategy__with_locked_asset(gov, asset, chain, vault, create_locked_strategy):
    strategy = create_locked_strategy(vault)
    amount = 10 * 10**18
    locked_amount = 10**18

    actions.airdrop_asset(gov, asset, strategy, amount)
    assert asset.balanceOf(strategy) == amount
    assert strategy.withdrawable() == amount

    # lock funds for one day
    strategy.setLockedFunds(locked_amount, 3600 * 24, sender=gov)
    unlocked = amount - locked_amount
    assert strategy.withdrawable() == unlocked

    # check lock after half day
    chain.pending_timestamp += 3600 * 12
    strategy.freeLockedFunds(sender=gov)
    assert strategy.withdrawable() == unlocked

    # check lock after full day
    chain.pending_timestamp += 3600 * 12
    strategy.freeLockedFunds(sender=gov)
    assert strategy.withdrawable() == amount

    # test can lock again
    strategy.setLockedFunds(locked_amount, 3600 * 24, sender=gov)
    unlocked = amount - locked_amount
    assert strategy.withdrawable() == unlocked
