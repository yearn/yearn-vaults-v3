import pytest
from utils.constants import MAX_INT

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
def whale(accounts):
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
    def create_vault(asset, deposit_limit=MAX_INT):
        vault = gov.deploy(project.VaultV3, asset)
        # set vault deposit
        vault.setDepositLimit(deposit_limit, sender=gov)
        # set up fee manager
        vault.setFeeManager(fee_manager.address, sender=gov)
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

    # make it so vault has some AUM to start
    asset.mint(gov.address, 10**18, sender=gov)
    asset.approve(vault.address, asset.balanceOf(gov) // 2, sender=gov)
    vault.deposit(asset.balanceOf(gov) // 2, gov.address, sender=gov)
    yield vault


# create default liquid strategy with 0 fee
@pytest.fixture(scope="session")
def strategy(gov, vault, create_strategy):
    strategy = create_strategy(vault)
    vault.addStrategy(strategy.address, sender=gov)
    strategy.setMinDebt(0, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def locked_strategy(gov, vault, create_locked_strategy):
    strategy = create_locked_strategy(vault)
    vault.addStrategy(strategy.address, sender=gov)
    strategy.setMinDebt(0, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def lossy_strategy(gov, vault, create_lossy_strategy):
    strategy = create_lossy_strategy(vault)
    vault.addStrategy(strategy.address, sender=gov)
    strategy.setMinDebt(0, sender=gov)
    strategy.setMaxDebt(MAX_INT, sender=gov)
    yield strategy


@pytest.fixture(scope="session")
def fee_manager(project, gov):
    fee_manager = gov.deploy(project.FeeManager)
    yield fee_manager
