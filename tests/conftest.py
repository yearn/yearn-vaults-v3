import pytest
from ape import chain
from ape.types import ContractLog
from eth_account.messages import encode_typed_data
from utils.constants import MAX_INT, ROLES, WEEK
import time
import os
from web3 import Web3, HTTPProvider
from hexbytes import HexBytes

# we default to local node
w3 = Web3(HTTPProvider(os.getenv("CHAIN_PROVIDER", "http://127.0.0.1:8545")))


# Accounts
@pytest.fixture(scope="session")
def gov(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def fish_amount(asset):
    # Working always with 10_000.00
    yield 10 ** (asset.decimals() + 4)


@pytest.fixture(scope="session")
def half_fish_amount(fish_amount):
    yield fish_amount // 2


@pytest.fixture(scope="session")
def fish(accounts, asset, gov, fish_amount):
    fish = accounts[1]
    asset.mint(fish.address, fish_amount, sender=gov)
    yield fish


@pytest.fixture(scope="session")
def whale_amount(asset):
    # Working always with 1_000_000.00
    yield 10 ** (asset.decimals() + 6)


@pytest.fixture(scope="session")
def whale(accounts, asset, gov, whale_amount):
    whale = accounts[2]
    asset.mint(whale.address, whale_amount, sender=gov)
    yield whale


@pytest.fixture(scope="session")
def bunny(accounts):
    yield accounts[3]


@pytest.fixture(scope="session")
def doggie(accounts):
    yield accounts[4]


@pytest.fixture(scope="session")
def panda(accounts):
    yield accounts[5]


@pytest.fixture(scope="session")
def woofy(accounts):
    yield accounts[6]


@pytest.fixture(scope="session")
def rewards(accounts):
    yield accounts[7]


@pytest.fixture(scope="session")
def strategist(accounts):
    yield accounts[8]


@pytest.fixture(scope="session")
def guardian(accounts):
    yield accounts[9]


@pytest.fixture(scope="session")
def management(accounts):
    yield accounts[10]


@pytest.fixture(scope="session")
def keeper(accounts):
    yield accounts[11]


# Expects a comma separated string of token decimals or real tokens to test with (e.g. "6,8,18,usdt")
# Set you ENV variable 'TOKENS_TO_TEST' to desire decimals for local testing
TOKENS_TO_TEST = os.getenv("TOKENS_TO_TEST", default="18").split(",")


@pytest.fixture(
    scope="session",
    params=TOKENS_TO_TEST,
)
def asset(create_token, mock_real_token, request):
    try:
        token_decimals = int(request.param)
        # We assume is the number of decimals of the token
        return create_token("asset", decimals=token_decimals)
    except:
        # We assume is the name of the real token to test with
        return mock_real_token(name=request.param)


# use this for token mock
@pytest.fixture(scope="session")
def mock_token(create_token):
    return create_token("mock")


# use this to use real tokens
@pytest.fixture(scope="session")
def mock_real_token(project, gov):
    def mock_real_token(name):
        if name == "usdt":
            return gov.deploy(project.TetherToken, 10**18, name, "USDT", 6)

    yield mock_real_token


# use this to create other tokens
@pytest.fixture(scope="session")
def create_token(project, gov):
    def create_token(name, decimals=18):
        return gov.deploy(project.Token, name, decimals)

    yield create_token


@pytest.fixture(scope="session")
def vault_original(project, gov):
    vault = gov.deploy(project.VaultV3)
    return vault.address


@pytest.fixture(scope="session")
def vault_factory(project, gov, vault_original):
    return gov.deploy(
        project.VaultFactory,
        "Vault V3 Factory test",
        vault_original,
        gov.address,
    )


@pytest.fixture(scope="session")
def set_factory_fee_config(project, gov, vault_factory):
    def set_factory_fee_config(fee_bps, fee_recipient):
        vault_factory.set_protocol_fee_recipient(fee_recipient, sender=gov)
        vault_factory.set_protocol_fee_bps(fee_bps, sender=gov)

    yield set_factory_fee_config


@pytest.fixture(scope="session")
def create_vault(project, gov, vault_factory):
    def create_vault(
        asset,
        governance=gov,
        deposit_limit=MAX_INT,
        max_profit_locking_time=WEEK,
        vault_name=None,
        vault_symbol="VV3",
    ):
        if not vault_name:
            # Every single vault that we create with the factory must have a different salt. The
            # salt is computed with the asset, name and symbol. Easiest way to create a vault
            # would be to create a unique name by adding a suffix. We will use 4 last digits of
            # time.time()
            vault_suffix = str(int(time.time()))[-4:]
            vault_name = f"Vault V3 {vault_suffix}"

        tx = vault_factory.deploy_new_vault(
            asset,
            vault_name,
            vault_symbol,
            governance,
            max_profit_locking_time,
            sender=gov,
        )
        event = list(tx.decode_logs(vault_factory.NewVault))
        vault = project.VaultV3.at(event[0].vault_address)

        vault.set_role(
            gov.address,
            ROLES.ADD_STRATEGY_MANAGER
            | ROLES.REVOKE_STRATEGY_MANAGER
            | ROLES.FORCE_REVOKE_MANAGER
            | ROLES.ACCOUNTANT_MANAGER
            | ROLES.QUEUE_MANAGER
            | ROLES.REPORTING_MANAGER
            | ROLES.DEBT_MANAGER
            | ROLES.MAX_DEBT_MANAGER
            | ROLES.DEPOSIT_LIMIT_MANAGER
            | ROLES.WITHDRAW_LIMIT_MANAGER
            | ROLES.MINIMUM_IDLE_MANAGER
            | ROLES.PROFIT_UNLOCK_MANAGER
            | ROLES.DEBT_PURCHASER
            | ROLES.EMERGENCY_MANAGER,
            sender=gov,
        )

        # set vault deposit
        vault.set_deposit_limit(deposit_limit, sender=gov)

        return vault

    yield create_vault


# create default liquid strategy with 0 fee
@pytest.fixture(scope="session")
def create_strategy(project, strategist, gov, vault_factory):
    def create_strategy(vault):
        return strategist.deploy(
            project.MockTokenizedStrategy,
            vault_factory.address,
            vault.asset(),
            "Mock Tokenized Strategy",
            strategist,
            gov,
        )

    yield create_strategy


# create locked strategy with 0 fee
@pytest.fixture(scope="session")
def create_locked_strategy(project, strategist):
    def create_locked_strategy(vault):
        return strategist.deploy(project.ERC4626LockedStrategy, vault, vault.asset())

    yield create_locked_strategy


# create lossy strategy with 0 fee
@pytest.fixture(scope="session")
def create_lossy_strategy(project, strategist, gov, vault_factory):
    def create_lossy_strategy(vault):
        return strategist.deploy(
            project.ERC4626LossyStrategy,
            vault_factory.address,
            vault.asset(),
            "Mock Tokenized Strategy",
            strategist,
            gov,
            vault,
        )

    yield create_lossy_strategy


# create faulty strategy with 0 fee
@pytest.fixture(scope="session")
def create_faulty_strategy(project, strategist):
    def create_faulty_strategy(vault):
        return strategist.deploy(project.ERC4626FaultyStrategy, vault, vault.asset())

    yield create_faulty_strategy


@pytest.fixture(scope="session")
def create_generic_strategy(project, strategist):
    def create_generic_strategy(asset):
        return strategist.deploy(project.Generic4626, asset)

    yield create_generic_strategy


@pytest.fixture(scope="session")
def vault(gov, asset, create_vault):
    vault = create_vault(asset)
    yield vault


# create default liquid strategy with 0 fee
@pytest.fixture(scope="session")
def strategy(gov, vault, create_strategy):
    strategy = create_strategy(vault)
    vault.add_strategy(strategy.address, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def locked_strategy(gov, vault, create_locked_strategy):
    strategy = create_locked_strategy(vault)
    vault.add_strategy(strategy.address, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def lossy_strategy(gov, vault, create_lossy_strategy):
    strategy = create_lossy_strategy(vault)
    vault.add_strategy(strategy.address, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def faulty_strategy(gov, vault, create_faulty_strategy):
    strategy = create_faulty_strategy(vault)
    vault.add_strategy(strategy.address, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def generic_strategy(gov, vault, create_generic_strategy):
    strategy = create_generic_strategy(vault.asset())
    vault.add_strategy(strategy.address, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def deploy_accountant(project, gov):
    def deploy_accountant(vault):
        accountant = gov.deploy(project.Accountant, vault)
        # set up fee manager
        vault.set_accountant(accountant.address, sender=gov)
        return accountant

    yield deploy_accountant


@pytest.fixture(scope="session")
def deploy_flexible_accountant(project, gov):
    def deploy_flexible_accountant(vault):
        flexible_accountant = gov.deploy(project.FlexibleAccountant, vault)
        # set up fee manager
        vault.set_accountant(flexible_accountant.address, sender=gov)
        return flexible_accountant

    yield deploy_flexible_accountant


@pytest.fixture(scope="session")
def deploy_faulty_accountant(project, gov):
    def deploy_faulty_accountant(vault):
        faulty_accountant = gov.deploy(project.FaultyAccountant, vault)
        # set up fee manager
        vault.set_accountant(faulty_accountant.address, sender=gov)
        return faulty_accountant

    yield deploy_faulty_accountant


@pytest.fixture(scope="session")
def deploy_limit_module(project, gov):
    def deploy_limit_module(
        deposit_limit=MAX_INT, withdraw_limit=MAX_INT, whitelist=False
    ):
        limit_module = gov.deploy(
            project.LimitModule, deposit_limit, withdraw_limit, whitelist
        )
        return limit_module

    yield deploy_limit_module


@pytest.fixture(scope="session")
def mint_and_deposit_into_strategy(gov, asset):
    def mint_and_deposit_into_strategy(
        strategy, account=gov, amount_to_mint=10**18, amount_to_deposit=None
    ):
        if amount_to_deposit == None:
            amount_to_deposit = amount_to_mint

        asset.mint(account.address, amount_to_mint, sender=gov)

        asset.approve(strategy.address, amount_to_deposit, sender=account)
        strategy.deposit(amount_to_deposit, account.address, sender=account)

    yield mint_and_deposit_into_strategy


@pytest.fixture(scope="session")
def mint_and_deposit_into_vault(gov, asset):
    def mint_and_deposit_into_vault(
        vault, account=gov, amount_to_mint=10**18, amount_to_deposit=None
    ):
        if amount_to_deposit == None:
            amount_to_deposit = amount_to_mint

        asset.mint(account.address, amount_to_mint, sender=gov)

        asset.approve(vault.address, amount_to_deposit, sender=account)
        vault.deposit(amount_to_deposit, account.address, sender=account)

    yield mint_and_deposit_into_vault


@pytest.fixture(scope="session")
def sign_vault_permit(chain):
    def sign_vault_permit(
        vault,
        owner,
        spender: str,
        allowance: int = MAX_INT,
        deadline: int = 0,
        override_nonce=None,
    ):
        name = "Yearn Vault"
        version = vault.apiVersion()
        if override_nonce:
            nonce = override_nonce
        else:
            nonce = vault.nonces(owner.address)
        data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "Permit": [
                    {"name": "owner", "type": "address"},
                    {"name": "spender", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "nonce", "type": "uint256"},
                    {"name": "deadline", "type": "uint256"},
                ],
            },
            "domain": {
                "name": name,
                "version": version,
                "chainId": chain.chain_id,
                "verifyingContract": str(vault),
            },
            "primaryType": "Permit",
            "message": {
                "owner": owner.address,
                "spender": spender,
                "value": allowance,
                "nonce": nonce,
                "deadline": deadline,
            },
        }
        permit = encode_typed_data(full_message=data)
        return owner.sign_message(permit)

    return sign_vault_permit


@pytest.fixture(scope="session")
def user_deposit():
    def user_deposit(user, vault, token, amount) -> ContractLog:
        initial_balance = token.balanceOf(vault)
        if token.allowance(user, vault) < amount:
            token.approve(vault.address, MAX_INT, sender=user)
        tx = vault.deposit(amount, user.address, sender=user)
        assert token.balanceOf(vault) == initial_balance + amount
        return tx

    return user_deposit


@pytest.fixture(scope="session")
def airdrop_asset():
    def airdrop_asset(gov, asset, target, amount):
        asset.mint(target, amount, sender=gov)

    return airdrop_asset


@pytest.fixture(scope="session")
def add_strategy_to_vault():
    # used for new adding a new strategy to vault with unlimited max debt settings
    def add_strategy_to_vault(user, strategy, vault):
        vault.add_strategy(strategy.address, sender=user)
        strategy.setMaxDebt(MAX_INT, sender=user)

    return add_strategy_to_vault


# used to add debt to a strategy
@pytest.fixture(scope="session")
def add_debt_to_strategy():
    def add_debt_to_strategy(user, strategy, vault, target_debt: int):
        vault.update_max_debt_for_strategy(strategy.address, target_debt, sender=user)
        vault.update_debt(strategy.address, target_debt, sender=user)

    return add_debt_to_strategy


@pytest.fixture(scope="session")
def set_fees_for_strategy():
    def set_fees_for_strategy(
        gov, strategy, accountant, management_fee, performance_fee, refund_ratio=0
    ):
        accountant.set_management_fee(strategy.address, management_fee, sender=gov)
        accountant.set_performance_fee(strategy.address, performance_fee, sender=gov)
        accountant.set_refund_ratio(strategy.address, refund_ratio, sender=gov)

    return set_fees_for_strategy


@pytest.fixture(scope="session")
def initial_set_up(
    create_vault,
    create_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    airdrop_asset,
    fish_amount,
    deploy_flexible_accountant,
    set_fees_for_strategy,
):
    def initial_set_up(
        asset,
        gov,
        debt_amount,
        user,
        management_fee=0,
        performance_fee=0,
        refund_ratio=0,
        accountant_mint=fish_amount // 10,
    ):
        """ """
        vault = create_vault(asset)
        airdrop_asset(gov, asset, gov, fish_amount)
        strategy = create_strategy(vault)

        accountant = None
        if management_fee or performance_fee or refund_ratio:
            accountant = deploy_flexible_accountant(vault)
            set_fees_for_strategy(
                gov,
                strategy,
                accountant,
                management_fee,
                performance_fee,
                refund_ratio,
            )

            if accountant_mint:
                airdrop_asset(gov, asset, accountant, accountant_mint)

        # Deposit assets to vault and get strategy ready
        user_deposit(user, vault, asset, debt_amount)
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, debt_amount)

        return vault, strategy, accountant

    return initial_set_up


@pytest.fixture(scope="session")
def initial_set_up_lossy(
    create_vault,
    create_lossy_strategy,
    user_deposit,
    add_strategy_to_vault,
    add_debt_to_strategy,
    airdrop_asset,
    fish_amount,
    deploy_flexible_accountant,
    set_fees_for_strategy,
):
    def initial_set_up_lossy(
        asset,
        gov,
        debt_amount,
        user,
        management_fee=0,
        performance_fee=0,
        refund_ratio=0,
        accountant_mint=0,
    ):
        """ """
        vault = create_vault(asset)
        airdrop_asset(gov, asset, gov, fish_amount)
        strategy = create_lossy_strategy(vault)

        accountant = None
        if management_fee or performance_fee or refund_ratio:
            accountant = deploy_flexible_accountant(vault)
            set_fees_for_strategy(
                gov,
                strategy,
                accountant,
                management_fee,
                performance_fee,
                refund_ratio,
            )
            if accountant_mint:
                airdrop_asset(gov, asset, accountant, accountant_mint)

        # Deposit assets to vault and get strategy ready
        user_deposit(user, vault, asset, debt_amount)
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, debt_amount)

        return vault, strategy, accountant

    return initial_set_up_lossy
