// SPDX-License-Identifier: GPL-3.0-or-later
pragma solidity >=0.8.18;

struct AddressSet {
    address[] addrs;
    mapping(address => bool) saved;
}

library LibAddressSet {
    function add(AddressSet storage s, address addr) internal {
        if (!s.saved[addr]) {
            s.addrs.push(addr);
            s.saved[addr] = true;
        }
    }

    function contains(
        AddressSet storage s,
        address addr
    ) internal view returns (bool) {
        return s.saved[addr];
    }

    function count(AddressSet storage s) internal view returns (uint256) {
        return s.addrs.length;
    }

    function rand(
        AddressSet storage s,
        uint256 seed
    ) internal view returns (address) {
        if (s.addrs.length > 0) {
            return s.addrs[seed % s.addrs.length];
        } else {
            return address(0);
        }
    }

    function addresses(
        AddressSet storage s
    ) internal view returns (address[] memory _addrs) {
        return s.addrs;
    }
}
