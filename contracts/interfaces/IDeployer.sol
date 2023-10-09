// SPDX-License-Identifier: MIT
pragma solidity 0.8.18;

interface IDeployer {
    event Deployed(address addr, uint256 salt);

    function deploy(bytes memory code, uint256 salt) external;
}
