// SPDX-License-Identifier: GPL-3.0
pragma solidity 0.8.14;

import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {IVault} from "../interfaces/IVault.sol";
import {IStrategy} from "../interfaces/IStrategy.sol";

/**
 * @title Yearn Base Strategy
 * @author yearn.finance
 * @notice
 *  BaseStrategy implements all of the required functionality to interoperate
 *  closely with the Vault contract. This contract should be inherited and the
 *  abstract methods implemented to adapt the Strategy to the particular needs
 *  it has to create a return.
 *
 */
abstract contract BaseStrategy is IStrategy {
  using SafeERC20 for IERC20;

  address public override vault;
  address public override asset;

  constructor(address _vault) {
    _initialize(_vault);
  }

  /**
   * @notice
   *  Initializes the Strategy, this is called only once, when the
   *  contract is deployed.
   * @dev `_vault` should implement `VaultAPI`.
   * @param _vault The address of the Vault responsible for this Strategy.
   */
  function _initialize(address _vault) internal {
    if (address(asset) != address(0)) revert StrategyAlreadyInitialized();

    vault = _vault;
    asset = IVault(vault).asset();
    // using approve since initialization is only called once
    IERC20(asset).approve(_vault, type(uint256).max); // Give Vault unlimited access (might save gas)
    // TODO: there is risk of running out of allowance ^^
  }

  function _onlyEmergencyAuthorized() internal view {
    // TODO: vault access control
    // if (IVault(vault).hasRole(RoleNames.GOVERNANCE, msg.sender) || IVault(vault).hasRole(RoleNames.MANAGEMENT, msg.sender)) {
    //   return;
    // }
    revert NoAccess();
  }

  function _onlyKeepers() internal view {
    // TODO: vault access control
    // if (
    //   IVault(vault).hasRole(RoleNames.KEEPER, msg.sender) ||
    //   IVault(vault).hasRole(RoleNames.GOVERNANCE, msg.sender) ||
    //   IVault(vault).hasRole(RoleNames.MANAGEMENT, msg.sender)
    // ) {
    //   return;
    // }

    revert NoAccess();
  }

  function _onlyGovernance() internal view {
    // TODO: vault access control
    // if (IVault(vault).hasRole(RoleNames.GOVERNANCE, msg.sender)) return;

    revert NoAccess();
  }

  function _onlyVault() internal view {
    if (msg.sender == vault) return;
    revert NoAccess();
  }

  modifier onlyEmergencyAuthorized() {
    _onlyEmergencyAuthorized();
    _;
  }

  modifier onlyGovernance() {
    _onlyGovernance();
    _;
  }

  modifier onlyKeepers() {
    _onlyKeepers();
    _;
  }

  modifier onlyVault() {
    _onlyVault();
    _;
  }

  function apiVersion() public pure override returns (uint256) {
    return 1000;
  }

  function harvest() external override onlyKeepers {
    _harvest();
  }

  function invest() external override onlyKeepers {
    _invest();
  }

  function freeFunds(uint256 _amount) external override onlyVault returns (uint256 amountFreed) {
    return _freeFunds(_amount);
  }

  function migrate(address _newStrategy) external onlyVault {
    _migrate(_newStrategy);
  }

  function emergencyFreeFunds(uint256 _amount) external override onlyVault {
    _emergencyFreeFunds(_amount);
  }

  function _harvest() internal virtual;

  function _invest() internal virtual;

  function _freeFunds(uint256 _amount) internal virtual returns (uint256 amountFreed);

  function _emergencyFreeFunds(uint256 _amount) internal virtual;

  function _migrate(address _newStrategy) internal virtual;

  function _protectedTokens() internal view virtual returns (address[] memory);

  function sweep(address _token) external onlyGovernance {
    if (_token == address(asset)) {
      revert ProtectedToken(_token);
    }

    address[] memory protectedTokens = _protectedTokens();
    for (uint256 i; i < protectedTokens.length; i++) {
      if (_token == protectedTokens[i]) {
        revert ProtectedToken(protectedTokens[i]);
      }
    }

    IERC20(_token).safeTransfer(msg.sender, IERC20(_token).balanceOf(address(this)));
  }
}
