def check_vault_empty(vault):
    assert vault.totalAssets() == 0
    assert vault.totalSupply() == 0
    assert vault.totalIdle() == 0
    assert vault.totalDebt() == 0
