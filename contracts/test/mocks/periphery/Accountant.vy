# @version 0.3.7

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


# STRUCTS #
struct Fee:
    management_fee: uint256
    performance_fee: uint256


# CONSTANTS #
MAX_BPS: constant(uint256) = 10_000
MAX_SHARE: constant(uint256) = 7_500
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
    """ """
    total_refunds: uint256 = 0

    # management_fee is charged in both profit and loss scenarios
    strategy_params: StrategyParams = IVault(msg.sender).strategies(strategy)
    fee: Fee = self.fees[strategy]
    duration: uint256 = block.timestamp - strategy_params.last_report

    #management_fee
    total_fees: uint256 = (
        (strategy_params.current_debt)
        * duration
        * fee.management_fee
        / MAX_BPS
        / SECS_PER_YEAR
    )

    if gain > 0:
        total_fees += (gain * fee.performance_fee) / MAX_BPS
        # ensure fee does not exceed more than 75% of gain
        maximum_fee: uint256 = (gain * MAX_SHARE) / MAX_BPS
        # test with min?
        if total_fees > maximum_fee:
            return (maximum_fee, 0)
    else:
        # Now taking loss from its own funds. In the future versions could be from different mechanisms
        asset_balance: uint256= ERC20(self.asset).balanceOf(self)
        refund_ratio: uint256 = self.refund_ratios[strategy]
        total_refunds = loss * refund_ratio / MAX_BPS
        if total_refunds > 0:
            # TODO: permissions implications. msg.sender should only be vault
            self.erc20_safe_approve(IVault(self.asset).asset(), msg.sender, total_refunds)
        
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
    assert performance_fee <= self._performance_fee_threshold(), "exceeds performance fee threshold"
    self.fees[strategy].performance_fee = performance_fee
    log UpdatePerformanceFee(performance_fee)


@external
def set_management_fee(strategy: address, management_fee: uint256):
    assert msg.sender == self.fee_manager, "not fee manager"
    assert management_fee <= self._management_fee_threshold(), "exceeds management fee threshold"
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
    assert self.future_fee_manager != ZERO_ADDRESS, "future fee manager != zero address"
    future_fee_manager: address = self.future_fee_manager
    self.fee_manager = future_fee_manager
    log ApplyFeeManager(future_fee_manager)


@view
@external
def performance_fee_threshold() -> uint256:
    return self._performance_fee_threshold()


@view
@internal
def _performance_fee_threshold() -> uint256:
    return MAX_BPS / 2


@view
@external
def management_fee_threshold() -> uint256:
    return self._management_fee_threshold()


@view
@internal
def _management_fee_threshold() -> uint256:
    return MAX_BPS
