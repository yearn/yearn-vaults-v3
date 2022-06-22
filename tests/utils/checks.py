def check_vault_empty(vault):
    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0


def check_revoked_strategy(strategy_params):
    assert strategy_params.activation == 0
    assert strategy_params.lastReport == 0
    assert strategy_params.currentDebt == 0
    assert strategy_params.maxDebt == 0
    assert strategy_params.totalGain == 0
    assert strategy_params.totalLoss == 0
