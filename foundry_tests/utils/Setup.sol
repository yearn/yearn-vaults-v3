// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.18;

import {ExtendedTest} from "./ExtendedTest.sol";

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";
import {ERC20Mock} from "@openzeppelin/contracts/mocks/ERC20Mock.sol";

import {IVault} from "../../contracts/interfaces/IVault.sol";
import {Roles} from "../../contracts/interfaces/Roles.sol";
import {IVaultFactory} from "../../contracts/interfaces/IVaultFactory.sol";

import {VyperDeployer} from "./VyperDeployer.sol";

contract Setup is ExtendedTest {
    IVault public vault;
    ERC20Mock public asset;
    IVaultFactory public vaultFactory;
    VyperDeployer public vyperDeployer;

    address public daddy = address(69);
    address public vaultManagement = address(2);

    uint256 public maxFuzzAmount = 1e30;

    function setUp() public virtual {
        vyperDeployer = new VyperDeployer();

        vaultFactory = setupFactory();

        asset = new ERC20Mock();

        vault = IVault(setUpVault());

        vm.label(address(vault), "Vault");
        vm.label(address(asset), "Asset");
        vm.label(address(vaultFactory), "Vault Factory");
        vm.label(daddy, "Daddy");
        vm.label(vaultManagement, "Vault management");
    }

    function setupFactory() public returns (IVaultFactory _factory) {
        address original = vyperDeployer.deployContract(
            "contracts/",
            "VaultV3"
        );

        bytes memory args = abi.encode("Test vault Factory", original, daddy);

        _factory = IVaultFactory(
            vyperDeployer.deployContract("contracts/", "VaultFactory", args)
        );
    }

    function setUpVault() public returns (IVault) {
        IVault _vault = IVault(
            vaultFactory.deploy_new_vault(
                address(asset),
                "Test vault",
                "tsVault",
                daddy,
                10 days
            )
        );

        vm.prank(daddy);
        // Give the vault manager all the roles
        _vault.set_role(vaultManagement, Roles.ALL);

        vm.prank(vaultManagement);
        _vault.set_deposit_limit(type(uint256).max);

        return _vault;
    }
}
