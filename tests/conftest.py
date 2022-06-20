import pytest

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
def shark_amount():
    yield 10**20


@pytest.fixture(scope="session")
def shark(accounts, asset, gov, shark_amount):
    shark = accounts[2]
    asset.mint(shark.address, shark_amount, sender=gov)
    yield shark


@pytest.fixture(scope="session")
def whale_amount():
    yield 10**22


@pytest.fixture(scope="session")
def whale(accounts):
    whale = accounts[3]
    asset.mint(whale.address, whale_amount, sender=gov)
    yield whale


@pytest.fixture(scope="session")
def bunny(accounts):
    yield accounts[4]


@pytest.fixture(scope="session")
def doggie(accounts):
    yield accounts[5]


@pytest.fixture(scope="session")
def panda(accounts):
    yield accounts[6]


@pytest.fixture(scope="session")
def woofy(accounts):
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


@pytest.fixture(scope="session")
def rewards(accounts):
    yield accounts[12]


# use this for general asset mock
@pytest.fixture(scope="session")
def asset(project, gov):
    return gov.deploy(project.Token, "asset")


# use this for token mock
@pytest.fixture(scope="session")
def mock_token(project, gov):
    return gov.deploy(project.Token, "mock")


# use this to create other tokens
@pytest.fixture(scope="session")
def create_token(project, gov):
    def create_token(name):
        return gov.deploy(project.Token, name)

    yield create_token


@pytest.fixture(scope="session")
def create_vault(project, gov):
    def create_vault(asset):
        return gov.deploy(project.VaultV3, asset)

    yield create_vault


# create default liquid strategy with 0 fee
@pytest.fixture(scope="session")
def create_strategy(project, strategist):
    def create_strategy(vault):
        return strategist.deploy(project.BaseStrategyLiquid, vault)

    yield create_strategy


@pytest.fixture
def vault(gov, asset, create_vault):
    vault = create_vault(asset)

    # Make it so vault has some AUM to start
    asset.mint(gov.address, 10**18, sender=gov)
    asset.approve(vault.address, asset.balanceOf(gov) // 2, sender=gov)
    vault.deposit(asset.balanceOf(gov) // 2, gov.address, sender=gov)
    yield vault


# create default liquid strategy with 0 fee
@pytest.fixture
def strategy(gov, vault, create_strategy):
    strategy = create_strategy(vault)
    vault.addStrategy(strategy.address, sender=gov)
    yield strategy
