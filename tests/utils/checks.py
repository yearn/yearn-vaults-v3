def check_vault_empty(vault):
    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0


def check_revoked_strategy(strategy_params):
    assert strategy_params.activation == 0
    assert strategy_params.last_report == 0
    assert strategy_params.current_debt == 0
    assert strategy_params.max_debt == 0
