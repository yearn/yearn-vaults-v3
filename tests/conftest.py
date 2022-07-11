import pytest
from ape import chain
from eth_account.messages import encode_structured_data
from utils.constants import MAX_INT, ROLES

# Accounts


@pytest.fixture(scope="session")
def gov(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def fish_amount():
    yield 10**18


@pytest.fixture(scope="session")
def fish(accounts, asset, gov, fish_amount):
    fish = accounts[1]
    asset.mint(fish.address, fish_amount, sender=gov)
    yield fish


@pytest.fixture(scope="session")
def whale_amount():
    yield 10**22


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


# use this for general asset mock
@pytest.fixture(scope="session")
def asset(create_token):
    return create_token("asset")


# use this for token mock
@pytest.fixture(scope="session")
def mock_token(create_token):
    return create_token("mock")


# use this to create other tokens
@pytest.fixture(scope="session")
def create_token(project, gov):
    def create_token(name):
        return gov.deploy(project.Token, name)

    yield create_token


@pytest.fixture(scope="session")
def create_vault(project, gov, fee_manager):
    def create_vault(asset, governance=gov, deposit_limit=MAX_INT):
        vault = gov.deploy(project.VaultV3, asset, "VaultV3", "AV", governance)
        # set vault deposit
        vault.set_deposit_limit(deposit_limit, sender=gov)
        # set up fee manager
        vault.set_fee_manager(fee_manager.address, sender=gov)

        vault.set_role(
            gov.address, ROLES.STRATEGY_MANAGER | ROLES.DEBT_MANAGER, sender=gov
        )

        return vault

    yield create_vault


# create default liquid strategy with 0 fee
@pytest.fixture(scope="session")
def create_strategy(project, strategist):
    def create_strategy(vault):
        return strategist.deploy(project.LiquidStrategy, vault)

    yield create_strategy


# create locked strategy with 0 fee
@pytest.fixture(scope="session")
def create_locked_strategy(project, strategist):
    def create_locked_strategy(vault):
        return strategist.deploy(project.LockedStrategy, vault)

    yield create_locked_strategy


# create locked strategy with 0 fee
@pytest.fixture(scope="session")
def create_lossy_strategy(project, strategist):
    def create_lossy_strategy(vault):
        return strategist.deploy(project.LossyStrategy, vault)

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
    strategy.setMinDebt(0, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def locked_strategy(gov, vault, create_locked_strategy):
    strategy = create_locked_strategy(vault)
    vault.add_strategy(strategy.address, sender=gov)
    strategy.setMinDebt(0, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def lossy_strategy(gov, vault, create_lossy_strategy):
    strategy = create_lossy_strategy(vault)
    vault.add_strategy(strategy.address, sender=gov)
    strategy.setMinDebt(0, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def fee_manager(project, gov):
    fee_manager = gov.deploy(project.FeeManager)
    yield fee_manager


@pytest.fixture
def mint_and_deposit_into_vault(project, gov):
    def mint_and_deposit_into_vault(
        vault, account=gov, amount_to_mint=10**18, amount_to_deposit=None
    ):
        if amount_to_deposit == None:
            amount_to_deposit = amount_to_mint

        asset = project.Token.at(vault.asset())
        asset.mint(account.address, amount_to_mint, sender=account)
        asset.approve(vault.address, amount_to_deposit, sender=account)
        vault.deposit(amount_to_deposit, account.address, sender=account)

    yield mint_and_deposit_into_vault


@pytest.fixture
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
                    {"name": "chain_id", "type": "uint256"},
                    {"name": "verifying_contract", "type": "address"},
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
                "chain_id": chain.chain_id,
                "verifying_contract": str(vault),
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
        return owner.sign_message(permit).signature

    return sign_vault_permit
