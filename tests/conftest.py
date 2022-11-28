import pytest
from ape import chain
from ape.types import ContractLog
from eth_account.messages import encode_structured_data
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


# TODO: uncomment decimals to check different tokens
@pytest.fixture(
    scope="session",
    params=[
        ("create", 18),
        # ("create", 8),
        # ("create", 6),
        # ("mock", "usdt"),
    ],
)
def asset(create_token, mock_real_token, request):
    operation = request.param[0]
    arg = request.param[1]
    assert operation in ("create", "mock")

    if operation == "create":
        return create_token("asset", decimals=arg)
    elif operation == "mock":
        return mock_real_token(name=arg)


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
def vault_blueprint(project, gov):
    blueprint_bytecode = b"\xFE\x71\x00" + HexBytes(
        project.VaultV3.contract_type.deployment_bytecode.bytecode
    )  # ERC5202
    len_bytes = len(blueprint_bytecode).to_bytes(2, "big")
    deploy_bytecode = HexBytes(
        b"\x61" + len_bytes + b"\x3d\x81\x60\x0a\x3d\x39\xf3" + blueprint_bytecode
    )

    c = w3.eth.contract(abi=[], bytecode=deploy_bytecode)
    deploy_transaction = c.constructor()
    tx_info = {"from": gov.address, "value": 0, "gasPrice": 0}
    tx_hash = deploy_transaction.transact(tx_info)

    return w3.eth.get_transaction_receipt(tx_hash)["contractAddress"]


@pytest.fixture(scope="session")
def vault_factory(project, gov, vault_blueprint):
    return gov.deploy(project.VaultFactory, "Vault V3 Factory 0.0.1", vault_blueprint)


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
            ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER | ROLES.ACCOUNTING_MANAGER,
            sender=gov,
        )

        # set vault deposit
        vault.set_deposit_limit(deposit_limit, sender=gov)

        return vault

    yield create_vault


# create default liquid strategy with 0 fee
@pytest.fixture(scope="session")
def create_strategy(project, strategist):
    def create_strategy(vault):
        return strategist.deploy(project.ERC4626LiquidStrategy, vault, vault.asset())

    yield create_strategy


# create locked strategy with 0 fee
@pytest.fixture(scope="session")
def create_locked_strategy(project, strategist):
    def create_locked_strategy(vault):
        return strategist.deploy(project.ERC4626LockedStrategy, vault, vault.asset())

    yield create_locked_strategy


# create locked strategy with 0 fee
@pytest.fixture(scope="session")
def create_lossy_strategy(project, strategist):
    def create_lossy_strategy(vault):
        return strategist.deploy(project.ERC4626LossyStrategy, vault, vault.asset())

    yield create_lossy_strategy


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
        version = vault.api_version()
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
        permit = encode_structured_data(data)
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
        asset.mint(target.address, amount, sender=gov)

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
        accountant_deposit=fish_amount // 10,
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
            airdrop_asset(gov, asset, accountant, fish_amount)
            if accountant_deposit:
                user_deposit(accountant, vault, asset, accountant_deposit)

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
        accountant_deposit=fish_amount // 10,
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
            airdrop_asset(gov, asset, accountant, fish_amount)
            if accountant_deposit:
                user_deposit(accountant, vault, asset, accountant_deposit)

        # Deposit assets to vault and get strategy ready
        user_deposit(user, vault, asset, debt_amount)
        add_strategy_to_vault(gov, strategy, vault)
        add_debt_to_strategy(gov, strategy, vault, debt_amount)

        return vault, strategy, accountant

    return initial_set_up_lossy
