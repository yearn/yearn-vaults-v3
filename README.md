# Yearn V3 Vaults

This repository contains the Smart Contracts for Yearns V3 vault implementation.

[VaultFactory.vy](contracts/VaultFactory.vy) - The base factory that all vaults will be deployed from and used to configure protocol fees

[Vault.vy](contracts/VaultV3.vy) - The ERC4626 compliant Vault that will handle all logic associated with deposits, withdraws, strategy management, profit reporting etc.

## Requirements

This repository runs on [ApeWorx](https://www.apeworx.io/). A python based development tool kit.

You will need:
 - Python 3.8 or later
 - Linux or macOS
 - Windows: Install Windows Subsystem Linux (WSL) with Python 3.8 or later
 - [Hardhat](https://hardhat.org/) installed globally

## Installation

Fork the repository and clone onto your local device 

```
git clone https://github.com/user/yearn-vaults-v3
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

See the ApeWorx [documentation](https://docs.apeworx.io/ape/stable/) and [github](https://github.com/ApeWorX/ape) for more information.

You will need hardhat to run the test `yarn`
