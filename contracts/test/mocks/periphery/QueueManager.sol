// SPDX-License-Identifier: AGPL-3.0

pragma solidity 0.8.14;

contract QueueManager {
    address public governance;

    mapping(address => address[]) internal strategies;
    mapping(address => address[]) internal queue;
    mapping(address => bool) internal force;

    string public name;

    constructor() {
        name = "Generic Queue Manager";
        governance = msg.sender;
    }

    function withdraw_queue(address vault)
        public
        view
        returns (address[] memory)
    {
        return queue[vault];
    }

    function should_override(address vault) public view returns (bool) {
        return force[vault];
    }

    function setForce(address vault, bool _force) external {
        require(msg.sender == governance);
        force[vault] = _force;
    }

    function setQueue(address vault, address[] memory _queue) external {
        require(msg.sender == governance);
        require(_queue.length <= 10);
        queue[vault] = _queue;
    }
}
