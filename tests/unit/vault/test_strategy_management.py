import ape
from utils import actions, checks
from utils.constants import MAX_INT, ZERO_ADDRESS

def test_add_valid_strategy():
    # TODO: try to add a valid strategy and checks everything's been saved correctly
    return
    
def test_add_existing_strategy():
    # TODO: try to add a strategy that has been added already
    return


def test_add_wrong_asset_strategy():
    # TODO: try to add a strategy managing a different asset from the vault
    return


def test_add_wrong_vault_strategy():
    # TODO: try to add a strategy that is targetting a different vault
    return


def test_set_max_debt():
    # TODO: change the max debt of a newly added strategy
    return


def test_remove_strategy():
    # TODO: revoke an existing strategy successfully
    return


def test_remove_strategy_with_funds():
    # TODO: try to remove a strategy with debt in it
    return


def test_remove_non_existing_strategy():
    # TODO: try to remove a strategy that has not been added
    return


def test_migrate_strategy_no_funds():
    # TODO: successfully migrate a strategy
    return


def test_migrate_strategy_with_funds():
    # TODO: successfully migrate strategy with funds
    return

def test_migrate_non_existing_strategy():
    # TODO: try to migrate a strategy that does not exist
    return


def test_migrate_to_invalid_strategy(): 
    # TODO: try to migrate to an invalid strategy (wrong vault, wrong asset)
    return


