# @version 0.3.7

# FeeManager without any fee threshold

from vyper.interfaces import ERC20

# INTERFACES #
struct StrategyParams:
    activation: uint256
    last_report: uint256
    current_debt: uint256
    max_debt: uint256

interface IVault:
    def strategies(strategy: address) -> StrategyParams: view
    def asset() -> address: view
    def deposit(assets: uint256, receiver: address) -> uint256: nonpayable

# EVENTS #
event CommitFeeManager:
    fee_manager: address

event ApplyFeeManager:
    fee_manager: address

event UpdatePerformanceFee:
    performance_fee: uint256

event UpdateManagementFee:
    management_fee: uint256

event UpdateRefundRatio:
    refund_ratio: uint256

event DistributeRewards:
    rewards: uint256

event RefundStrategy:
    strategy: address
    loss: uint256
    refund: uint256


# STRUCTS #
struct Fee:
    management_fee: uint256
    performance_fee: uint256


# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000
# NOTE: A four-century period will be missing 3 of its 100 Julian leap years, leaving 97.
#       So the average year has 365 + 97/400 = 365.2425 days
#       ERROR(Julian): -0.0078
#       ERROR(Gregorian): -0.0003
#       A day = 24 * 60 * 60 sec = 86400 sec
#       365.2425 * 86400 = 31556952.0
SECS_PER_YEAR: constant(uint256) = 31_556_952  # 365.2425 days


# STORAGE #
fee_manager: public(address)
future_fee_manager: public(address)
fees: public(HashMap[address, Fee])
refund_ratios: public(HashMap[address, uint256])
asset: public(address)

@external
def __init__(asset: address):
    self.fee_manager = msg.sender
    self.asset = asset


@external
def report(strategy: address, gain: uint256, loss: uint256) -> (uint256, uint256):
    """
    """
    total_refunds: uint256 = 0

    performance_fee: uint256 = 0
    strategist_fee: uint256 = 0

    # management_fee is charged in both profit and loss scenarios
    strategy_params: StrategyParams = IVault(msg.sender).strategies(strategy)
    fee: Fee = self.fees[strategy]
    refund_ratio: uint256 = self.refund_ratios[strategy]
    duration: uint256 = block.timestamp - strategy_params.last_report

    total_fees: uint256 = (
        (strategy_params.current_debt)
        * duration
        * fee.management_fee
        / MAX_BPS
        / SECS_PER_YEAR
    )

    asset_balance: uint256= ERC20(IVault(self.asset).asset()).balanceOf(self)

    if gain > 0:
        total_fees += (gain * fee.performance_fee) / MAX_BPS
        total_refunds = min(asset_balance, gain * refund_ratio / MAX_BPS)
    else:
        # Now taking loss from its own funds. In the future versions could be from different mechanisms
        total_refunds = min(asset_balance, loss * refund_ratio / MAX_BPS)

    return (total_fees, total_refunds)

@internal
def erc20_safe_approve(token: address, spender: address, amount: uint256):
    # Used only to send tokens that are not the type managed by this Vault.
    # HACK: Used to handle non-compliant tokens like USDT
    response: Bytes[32] = raw_call(
        token,
        concat(
            method_id("approve(address,uint256)"),
            convert(spender, bytes32),
            convert(amount, bytes32),
        ),
        max_outsize=32,
    )
    if len(response) > 0:
        assert convert(response, bool), "Transfer failed!"



@external
def distribute(vault: ERC20):
    assert msg.sender == self.fee_manager, "not fee manager"
    rewards: uint256 = vault.balanceOf(self)
    vault.transfer(msg.sender, rewards)
    log DistributeRewards(rewards)


@external
def set_performance_fee(strategy: address, performance_fee: uint256):
    assert msg.sender == self.fee_manager, "not fee manager"
    self.fees[strategy].performance_fee = performance_fee
    log UpdatePerformanceFee(performance_fee)


@external
def set_management_fee(strategy: address, management_fee: uint256):
    assert msg.sender == self.fee_manager, "not fee manager"
    self.fees[strategy].management_fee = management_fee
    log UpdateManagementFee(management_fee)

@external
def set_refund_ratio(strategy: address, refund_ratio: uint256):
    assert msg.sender == self.fee_manager, "not fee manager"
    self.refund_ratios[strategy] = refund_ratio
    log UpdateRefundRatio(refund_ratio)


@external
def commit_fee_manager(future_fee_manager: address):
    assert msg.sender == self.fee_manager, "not fee manager"
    self.future_fee_manager = future_fee_manager
    log CommitFeeManager(future_fee_manager)


@external
def apply_fee_manager():
    assert msg.sender == self.fee_manager, "not fee manager"
    assert self.future_fee_manager != empty(address), "future fee manager != zero address"
    future_fee_manager: address = self.future_fee_manager
    self.fee_manager = future_fee_manager
    log ApplyFeeManager(future_fee_manager)
