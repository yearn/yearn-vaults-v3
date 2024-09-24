// SPDX-License-Identifier: AGPL-3.0
pragma solidity >=0.8.18;

import "forge-std/Script.sol";

///@notice This cheat codes interface is named _CheatCodes so you can use the CheatCodes interface in other testing files without errors
interface _CheatCodes {
    function ffi(string[] calldata) external returns (bytes memory);
}

// Deploy a contract to a deterministic address with create2
contract Deploy is Script {
    address constant HEVM_ADDRESS =
        address(bytes20(uint160(uint256(keccak256("hevm cheat code")))));

    /// @notice Initializes cheat codes in order to use ffi to compile Vyper contracts
    _CheatCodes cheatCodes = _CheatCodes(HEVM_ADDRESS);

    Deployer public deployer =
        Deployer(0xba5Ed099633D3B313e4D5F7bdc1305d3c28ba5Ed);

    function run() external {
        vm.startBroadcast();

        string[] memory cmds = new string[](2);
        cmds[0] = "vyper";
        cmds[1] = "contracts/VaultFactory.vy";

        ///@notice compile the Vyper contract and return the bytecode
        bytes memory _bytecode = cheatCodes.ffi(cmds);

        bytes memory args = abi.encode(
            "Yearn v3.0.3 Vault Factory",
            0xcA78AF7443f3F8FA0148b746Cb18FF67383CDF3f,
            0x6f3cBE2ab3483EC4BA7B672fbdCa0E9B33F88db8
        );

        //add args to the deployment bytecode
        bytes memory bytecode = abi.encodePacked(_bytecode, args);

        // Pick an unique salt
        uint256 salt = 48628676351035099281129189787297157113420477883337005618231542152101559208037;

        address contractAddress = deployer.deployCreate2(
            bytes32(salt),
            bytecode
        );

        console.log("Address is ", contractAddress);

        vm.stopBroadcast();
    }
}

interface Deployer {
    event ContractCreation(address indexed newContract, bytes32 indexed salt);

    function deployCreate3(
        bytes32 salt,
        bytes memory initCode
    ) external payable returns (address newContract);

    function deployCreate2(
        bytes32 salt,
        bytes memory initCode
    ) external payable returns (address newContract);
}
