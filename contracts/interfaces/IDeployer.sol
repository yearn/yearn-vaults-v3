// SPDX-License-Identifier: MIT
pragma solidity >=0.8.18;

interface IDeployer {
    event ContractCreation(address indexed newContract, bytes32 indexed salt);

    function deployCreate2(
        bytes32 salt,
        bytes memory initCode
    ) external payable returns (address newContract);
}
