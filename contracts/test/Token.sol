// SPDX-License-Identifier: MIT
pragma solidity >=0.8.18;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract Token is ERC20 {
    uint8 public decimals_;

    constructor(string memory _name, uint8 _decimals) ERC20(_name, _name) {
        decimals_ = _decimals;
    }

    function decimals() public view virtual override returns (uint8) {
        return decimals_;
    }

    function mint(address _to, uint256 _amount) external {
        _mint(_to, _amount);
    }
}
