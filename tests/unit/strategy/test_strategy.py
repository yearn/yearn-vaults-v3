import ape


# placeholder tests for test mocks
def test_liquid_strategy__with_fee(gov, vault, create_strategy):
    strategy = create_strategy(vault)
    fee = 500 # 5%

    strategy.setFee(fee, sender=gov)

    assert strategy.fee() == fee
