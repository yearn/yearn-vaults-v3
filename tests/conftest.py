import pytest

# Accounts


@pytest.fixture(scope="session")
def gov(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def strat_ms(accounts):
    yield accounts[1]


@pytest.fixture(scope="session")
def guardian(accounts):
    yield accounts[2]


@pytest.fixture(scope="session")
def management(accounts):
    yield accounts[3]


@pytest.fixture(scope="session")
def strategist(accounts):
    yield accounts[4]


@pytest.fixture(scope="session")
def keeper(accounts):
    yield accounts[5]


@pytest.fixture(scope="session")
def rewards(accounts):
    yield accounts[6]


@pytest.fixture(scope="session")
def fish_amount():
    yield 10**18


@pytest.fixture(scope="session")
def fish(accounts, asset, gov, fish_amount):
    fish = accounts[7]
    asset.mint(fish, fish_amount, sender=gov)
    yield fish


@pytest.fixture(scope="session")
def shark_amount():
    yield 10**20


@pytest.fixture(scope="session")
def shark(accounts, asset, gov, shark_amount):
    shark = accounts[8]
    asset.mint(shark, shark_amount, sender=gov)
    yield shark


@pytest.fixture(scope="session")
def whale_amount():
    yield 10**22


@pytest.fixture(scope="session")
def whale(accounts):
    whale = accounts[9]
    asset.mint(whale, whale_amount, sender=gov)
    yield whale


@pytest.fixture(scope="session")
def bunny(accounts):
    yield accounts[10]


@pytest.fixture(scope="session")
def doggie(accounts):
    yield accounts[11]


@pytest.fixture(scope="session")
def panda(accounts):
    yield accounts[12]


# use this for general asset mock
@pytest.fixture(scope="session")
def asset(project, gov):
    return gov.deploy(project.Token, "asset")


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
