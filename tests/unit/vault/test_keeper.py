import ape
from utils import checks
from utils.constants import MAX_INT, ROLES


def test_keeper_without_role__reverts(
    gov,
    fish,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    fish_amount,
):
    amount = fish_amount
    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)
    with ape.reverts():
        vault.tend_strategy(strategy, sender=fish)


def test_keeper_tends(
    gov,
    fish,
    asset,
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    fish_amount,
):
    amount = fish_amount
    vault = create_vault(asset)
    strategy = create_strategy(vault)

    # Deposit assets to vault and get strategy ready
    user_deposit(fish, vault, asset, amount)
    add_strategy_to_vault(gov, strategy, vault)
    add_debt_to_strategy(gov, strategy, vault, amount)

    vault.set_role(fish.address, ROLES.KEEPER, sender=gov)

    tx = vault.tend_strategy(strategy, sender=fish)
    event = list(tx.decode_logs(strategy.Tend))

    assert len(event) == 1

    
