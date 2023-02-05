// SPDX-License-Identifier: AGPL-3.0

pragma solidity 0.8.14;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {Math} from "@openzeppelin/contracts/utils/math/Math.sol";

interface IBaseFee {
    function isCurrentBaseFeeAcceptable() external view returns (bool);
}

abstract contract BaseStrategy is ERC20 {
    using SafeERC20 for ERC20;
    using Math for uint256;

    /*//////////////////////////////////////////////////////////////
                                 EVENTS
    //////////////////////////////////////////////////////////////*/

    event Deposit(
        address indexed caller,
        address indexed owner,
        uint256 assets,
        uint256 shares
    );

    event Withdraw(
        address indexed caller,
        address indexed receiver,
        address indexed owner,
        uint256 assets,
        uint256 shares
    );

    /*//////////////////////////////////////////////////////////////
                               IMMUTABLES
    //////////////////////////////////////////////////////////////*/

    ERC20 public immutable asset;

    /*//////////////////////////////////////////////////////////////
                            STORAGE
    //////////////////////////////////////////////////////////////*/

    uint256 public totalDebt;
    uint256 public totalIdle;
    address public management;

    modifier onlyManagement() {
        _onlyManagement();
        _;
    }

    function _onlyManagement() internal view {
        require(msg.sender == management, "not vault");
    }

    // TODO: Add support for non 18 decimal assets
    constructor(
        ERC20 _asset,
        string memory _name,
        string memory _symbol
    ) ERC20(_name, _symbol) {
        asset = _asset;
        management = msg.sender;
    }

    function totalAssets() public view returns (uint256) {
        return totalIdle + totalDebt;
    }

    // TODO: Make non-reentrant for all 4 deposit/withdraw functions

    function deposit(uint256 assets, address receiver)
        public
        virtual
        returns (uint256 shares)
    {
        // check lower than max
        require(
            assets <= maxDeposit(receiver),
            "ERC4626: deposit more than max"
        );
        // Check for rounding error since we round down in previewDeposit.
        require((shares = previewDeposit(assets)) != 0, "ZERO_SHARES");

        // Need to transfer before minting or ERC777s could reenter.
        asset.safeTransferFrom(msg.sender, address(this), assets);

        // mint
        _mint(receiver, shares);

        emit Deposit(msg.sender, receiver, assets, shares);

        // invest if applicable
        uint256 invested = _invest(assets);

        // adjust total Assets
        totalDebt += invested;
        totalIdle += (invested - assets);
    }

    function mint(uint256 shares, address receiver)
        public
        virtual
        returns (uint256 assets)
    {
        require(shares <= maxMint(receiver), "ERC4626: mint more than max");

        assets = previewMint(shares); // No need to check for rounding error, previewMint rounds up.

        // Need to transfer before minting or ERC777s could reenter.
        asset.safeTransferFrom(msg.sender, address(this), assets);

        _mint(receiver, shares);

        emit Deposit(msg.sender, receiver, assets, shares);

        // invest if applicable
        uint256 invested = _invest(assets);

        // adjust total Assets
        totalDebt += invested;
        totalIdle += (invested - assets);
    }

    function withdraw(
        uint256 assets,
        address receiver,
        address owner
    ) public virtual returns (uint256 shares) {
        require(
            assets <= maxWithdraw(owner),
            "ERC4626: withdraw more than max"
        );

        shares = previewWithdraw(assets); // No need to check for rounding error, previewWithdraw rounds up.

        if (msg.sender != owner) {
            _spendAllowance(owner, msg.sender, shares);
        }

        uint256 idle = totalIdle;
        uint256 withdrawn = idle >= assets ? _withdraw(assets) : 0;

        _burn(owner, shares);

        totalIdle -= idle > assets ? assets : idle;
        totalDebt -= withdrawn;

        asset.safeTransfer(receiver, assets);

        emit Withdraw(msg.sender, receiver, owner, assets, shares);
    }

    function redeem(
        uint256 shares,
        address receiver,
        address owner
    ) public virtual returns (uint256 assets) {
        require(shares <= maxRedeem(owner), "ERC4626: redeem more than max");

        if (msg.sender != owner) {
            _spendAllowance(owner, msg.sender, shares);
        }

        // Check for rounding error since we round down in previewRedeem.
        require((assets = previewRedeem(shares)) != 0, "ZERO_ASSETS");

        // withdraw if we dont have enough idle
        uint256 idle = totalIdle;
        uint256 withdrawn = idle >= assets ? _withdraw(assets) : 0;

        _burn(owner, shares);

        // adjust state variables
        totalIdle -= idle > assets ? assets : idle;
        totalDebt -= withdrawn;

        asset.safeTransfer(receiver, assets);

        emit Withdraw(msg.sender, receiver, owner, assets, shares);
    }

    // TODO: add locked shares or locked profit calculations based on how profits will be locked

    // TODO: import V3 type logic for reporting profits
    function report() external onlyManagement {
        // first account for all gains
        _tend();

        // calculate profit

        // lock shares etc
    }

    function tendTrigger() external view returns (bool) {
        return _tendTrigger();
    }

    /*//////////////////////////////////////////////////////////////
                            ACCOUNTING LOGIC
    //////////////////////////////////////////////////////////////*/

    function totalSupply() public view override returns (uint256) {
        return totalSupply() - unlockedShares();
    }

    function unlockedShares() public view returns (uint256) {
        // TODO: add unlocked shares logic
    }

    function convertToShares(uint256 assets)
        public
        view
        virtual
        returns (uint256)
    {
        uint256 supply = totalSupply(); // Saves an extra SLOAD if totalSupply is non-zero.

        return
            supply == 0
                ? assets
                : assets.mulDiv(supply, totalAssets(), Math.Rounding.Down);
    }

    function convertToAssets(uint256 shares)
        public
        view
        virtual
        returns (uint256)
    {
        uint256 supply = totalSupply(); // Saves an extra SLOAD if totalSupply is non-zero.

        return
            supply == 0
                ? shares
                : shares.mulDiv(totalAssets(), supply, Math.Rounding.Down);
    }

    function previewDeposit(uint256 assets)
        public
        view
        virtual
        returns (uint256)
    {
        return convertToShares(assets);
    }

    function previewMint(uint256 shares) public view virtual returns (uint256) {
        uint256 supply = totalSupply(); // Saves an extra SLOAD if totalSupply is non-zero.

        return
            supply == 0
                ? shares
                : shares.mulDiv(totalAssets(), supply, Math.Rounding.Up);
    }

    function previewWithdraw(uint256 assets)
        public
        view
        virtual
        returns (uint256)
    {
        uint256 supply = totalSupply(); // Saves an extra SLOAD if totalSupply is non-zero.

        return
            supply == 0
                ? assets
                : assets.mulDiv(supply, totalAssets(), Math.Rounding.Up);
    }

    function previewRedeem(uint256 shares)
        public
        view
        virtual
        returns (uint256)
    {
        return convertToAssets(shares);
    }

    /*//////////////////////////////////////////////////////////////
                     DEPOSIT/WITHDRAWAL LIMIT LOGIC
    //////////////////////////////////////////////////////////////*/

    function maxDeposit(address _owner) public view virtual returns (uint256) {
        return _maxDeposit(_owner);
    }

    function maxMint(address _owner) public view virtual returns (uint256) {
        return _maxMint(_owner);
    }

    function maxWithdraw(address _owner) public view virtual returns (uint256) {
        return _maxWithdraw(_owner);
    }

    function maxRedeem(address _owner) public view virtual returns (uint256) {
        return _maxRedeem(_owner);
    }

    /*//////////////////////////////////////////////////////////////
                    NEEDED TO OVERRIDEN BY STRATEGIST
    //////////////////////////////////////////////////////////////*/

    // Will attempt to free the 'amount' of assets and return the acutal amount
    function _withdraw(uint256 amount)
        internal
        virtual
        returns (uint256 withdrawnAmount);

    // will invest up to the amount of 'assets' and return the actual amount that was invested
    function _invest(uint256 assets)
        internal
        virtual
        returns (uint256 invested);

    /*//////////////////////////////////////////////////////////////
                    OPTIONAL TO OVERRIDE BY STRATEGIST
    //////////////////////////////////////////////////////////////*/

    function _tend() internal virtual {}

    function _tendTrigger() internal view virtual returns (bool) {}

    function _maxDeposit(address) internal view virtual returns (uint256) {
        return type(uint256).max;
    }

    function _maxMint(address) internal view virtual returns (uint256) {
        return type(uint256).max;
    }

    function _maxWithdraw(address owner)
        internal
        view
        virtual
        returns (uint256)
    {
        return convertToAssets(balanceOf(owner));
    }

    function _maxRedeem(address owner) internal view virtual returns (uint256) {
        return balanceOf(owner);
    }

    /*//////////////////////////////////////////////////////////////
                        HELPER FUNCTIONS
    //////////////////////////////////////////////////////////////*/

    function isBaseFeeAcceptable() internal view returns (bool) {
        return
            IBaseFee(0xb5e1CAcB567d98faaDB60a1fD4820720141f064F)
                .isCurrentBaseFeeAcceptable();
    }
}
