// SPDX-License-Identifier: MIT
pragma solidity 0.8.13;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract Token is ERC20 {
    constructor(string memory _name) ERC20(_name, _name) {}

    function mint(address _to, uint256 _amount) external {
        _mint(_to, _amount);
    }
}
