import ape
from ape import chain


def test__set_protocol_fees(gov, vault_factory):
    assert vault_factory.protocol_fee_config().fee_last_change == 0
    last_change = vault_factory.protocol_fee_config().fee_last_change
    tx = vault_factory.set_protocol_fee_bps(20, sender=gov)

    event = list(tx.decode_logs(vault_factory.UpdateProtocolFeeBps))
    assert event[0].old_fee_bps == 0
    assert event[0].new_fee_bps == 20

    assert vault_factory.protocol_fee_config().fee_bps == 20
    assert vault_factory.protocol_fee_config().fee_last_change > last_change


def test__set_protocol_fee_recipient(gov, vault_factory):
    tx = vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    event = list(tx.decode_logs(vault_factory.UpdateProtocolFeeRecipient))
    assert event[0].old_fee_recipient == "0x0000000000000000000000000000000000000000"
    assert event[0].new_fee_recipient == gov.address

    assert vault_factory.protocol_fee_config().fee_recipient == gov.address


def test__set_protocol_fee_recipient_by_bunny__reverts(bunny, vault_factory):
    with ape.reverts("not governance"):
        vault_factory.set_protocol_fee_recipient(bunny.address, sender=bunny)


def test__set_protocol_fees_too_high__reverts(gov, vault_factory):
    with ape.reverts("fee too high"):
        vault_factory.set_protocol_fee_bps(26, sender=gov)


def test__set_protocol_fees_by_bunny__reverts(bunny, vault_factory):
    with ape.reverts("not governance"):
        vault_factory.set_protocol_fee_bps(20, sender=bunny)
