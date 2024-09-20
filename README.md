# Yearn V3 Vaults

This repository contains the Smart Contracts for Yearns V3 vault implementation.

[VaultFactory.vy](contracts/VaultFactory.vy) - The base factory that all vaults will be deployed from and used to configure protocol fees

[Vault.vy](contracts/VaultV3.vy) - The ERC4626 compliant Vault that will handle all logic associated with deposits, withdraws, strategy management, profit reporting etc.

For the most updated deployment addresses see the [docs](https://docs.yearn.fi/developers/addresses/v3-contracts). And read more about V3 and how to manage your own multi strategy vault here https://docs.yearn.fi/developers/v3/overview

For the V3 strategy implementation see the [Tokenized Strategy](https://github.com/yearn/tokenized-strategy) repo.

## Requirements

This repository runs on [ApeWorx](https://www.apeworx.io/). A python based development tool kit.

You will need:
 - Python 3.8 or later
 - [Vyper 0.3.7](https://docs.vyperlang.org/en/stable/installing-vyper.html)
 - [Foundry](https://book.getfoundry.sh/getting-started/installation)
 - Linux or macOS
 - Windows: Install Windows Subsystem Linux (WSL) with Python 3.8 or later
 - [Hardhat](https://hardhat.org/) installed globally

## Installation

Fork the repository and clone onto your local device 

```
git clone --recursive https://github.com/user/yearn-vaults-v3
cd yearn-vaults-v3
```

Set up your python virtual environment and activate it.

```
python3 -m venv venv
source venv/bin/activate
```

Install requirements.

```
python3 -m pip install -r requirements.txt
yarn
```

Fetch the ape plugins:

```
ape plugins install .
```

Compile smart contracts with:

```
ape compile
```

and test smart contracts with:

```
ape test
```

To run the Foundry tests
 
NOTE: You will need to first compile with Ape before running foundry tests.
```
forge test
```

## Deployment

Deployments of the Vault Factory are done using create2 to be at a deterministic address on any EVM chain.

Check the [docs](https://docs.yearn.fi/developers/addresses/v3-contracts) for the most updated deployment address.

Deployments on new chains can be done permissionlessly by anyone using the included script.
```
ape run scripts/deploy.py --network YOUR_RPC_URL
```

If the deployments do not end at the same address you can also manually send the calldata used in the previous deployments on other chains.

### To make a contribution please follow the [guidelines](https://github.com/yearn/yearn-vaults-v3/bloc/master/CONTRIBUTING.md)

See the ApeWorx [documentation](https://docs.apeworx.io/ape/stable/) and [github](https://github.com/ApeWorX/ape) for more information.

You will need hardhat to run the test `yarn`