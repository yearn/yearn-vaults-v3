// SPDX-License-Identifier: MIT
pragma solidity 0.8.14;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract Token is ERC20 {
    uint8 public _decimals;

    constructor(string memory _name, uint8 decimals) ERC20(_name, _name) {
        _decimals = decimals;
    }

    function decimals() public view virtual override returns (uint8) {
        return _decimals;
    }

    function mint(address _to, uint256 _amount) external {
        _mint(_to, _amount);
    }
}
