// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.8.18;

import {MockTokenizedStrategy, ERC20} from "./MockTokenizedStrategy.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract YieldSource {
    using SafeERC20 for ERC20;

    ERC20 public asset;

    constructor(address _asset) {
        asset = ERC20(_asset);
        asset.safeApprove(msg.sender, type(uint256).max);
    }

    function deposit(uint256 _amount) external {
        asset.safeTransferFrom(msg.sender, address(this), _amount);
    }

    function withdraw(uint256 _amount) external {
        asset.safeTransfer(msg.sender, _amount);
    }
}

contract ERC4626LossyStrategy is MockTokenizedStrategy {
    using SafeERC20 for ERC20;

    int256 public withdrawingLoss;
    uint256 public lockedFunds;
    address public vault;
    address public yieldSource;

    constructor(
        address _factory,
        address _asset,
        string memory _name,
        address _management,
        address _keeper,
        address _vault
    ) MockTokenizedStrategy(_factory, _asset, _name, _management, _keeper) {
        yieldSource = address(new YieldSource(_asset));
        ERC20(_asset).safeApprove(yieldSource, type(uint256).max);
        // So we can record losses when it happens.
        _strategyStorage().management = address(this);
        vault = _vault;
    }

    // used to generate losses, accepts single arg to send losses to
    function setLoss(address _target, uint256 _loss) external {
        _strategyStorage().asset.safeTransferFrom(yieldSource, _target, _loss);
        // Record the loss
        MockTokenizedStrategy(address(this)).report();
    }

    function setWithdrawingLoss(int256 _loss) external {
        withdrawingLoss = _loss;
    }

    function setLockedFunds(uint256 _lockedFunds) external {
        lockedFunds = _lockedFunds;
    }

    function deployFunds(uint256 _amount) external override {
        YieldSource(yieldSource).deposit(_amount);
    }

    function freeFunds(uint256 _amount) external override {
        // Adjust the amount to withdraw.
        uint256 toWithdraw = uint256(int256(_amount) - withdrawingLoss);
        YieldSource(yieldSource).withdraw(toWithdraw);

        if (withdrawingLoss < 0) {
            // Over withdraw to the vault
            _strategyStorage().asset.safeTransfer(
                vault,
                uint256(-withdrawingLoss)
            );
        }
    }

    function harvestAndReport() external override returns (uint256) {
        return
            _strategyStorage().asset.balanceOf(address(this)) +
            _strategyStorage().asset.balanceOf(yieldSource);
    }

    function availableWithdrawLimit(
        address
    ) public view override returns (uint256) {
        return
            _strategyStorage().asset.balanceOf(address(this)) +
            _strategyStorage().asset.balanceOf(yieldSource) -
            lockedFunds;
    }
}
