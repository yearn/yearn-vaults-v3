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
def user(accounts):
    yield accounts[7]


@pytest.fixture(scope="session")
def bunny(accounts):
    yield accounts[8]


@pytest.fixture(scope="session")
def doggie(accounts):
    yield accounts[8]


@pytest.fixture(scope="session")
def panda(accounts):
    yield accounts[8]


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


@pytest.fixture(autouse=True)
def mint_asset(asset, gov, user):
    amount = 1_000_000 * 10**18
    asset.mint(user, amount, sender=gov)
