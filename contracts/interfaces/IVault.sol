// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {IERC4626} from "@openzeppelin/contracts/interfaces/IERC4626.sol";

interface IVault is IERC4626 {
    // ROLES

    struct StrategyParams {
        uint256 activation;
        uint256 last_report;
        uint256 current_debt;
        uint256 max_debt;
    }

    function FACTORY() external view returns (uint256);

    function strategies(address) external view returns (StrategyParams memory);

    function default_queue(uint256) external view returns (address);

    
}
