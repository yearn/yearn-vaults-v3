import ape
from ape import chain
from utils.constants import ZERO_ADDRESS


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
    assert event[0].old_fee_recipient == ZERO_ADDRESS
    assert event[0].new_fee_recipient == gov.address

    assert vault_factory.protocol_fee_config().fee_recipient == gov.address


def test__set_custom_protocol_fee(gov, vault_factory, create_vault, asset):
    # Set the default protocol fee recipient
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    assert vault_factory.protocol_fee_config().fee_recipient == gov.address
    assert vault_factory.protocol_fee_config().fee_bps == 0
    last_change = vault_factory.protocol_fee_config().fee_last_change

    vault = create_vault(asset)

    # Make sure its currently set to the default settings.
    assert (
        vault_factory.protocol_fee_config(sender=vault.address).fee_recipient
        == gov.address
    )
    assert vault_factory.protocol_fee_config(sender=vault.address).fee_bps == 0
    assert (
        vault_factory.protocol_fee_config(sender=vault.address).fee_last_change
        == last_change
    )

    new_fee = int(20)
    # Set custom fee for new vault.
    tx = vault_factory.set_custom_protocol_fee_bps(vault.address, new_fee, sender=gov)

    event = list(tx.decode_logs(vault_factory.UpdateCustomProtocolFee))

    assert len(event) == 1
    assert event[0].vault == vault.address
    assert event[0].new_custom_protocol_fee == new_fee

    # Should now be different than default
    assert (
        vault_factory.protocol_fee_config(sender=vault.address).fee_recipient
        == gov.address
    )
    assert vault_factory.protocol_fee_config(sender=vault.address).fee_bps == new_fee
    assert (
        vault_factory.protocol_fee_config(sender=vault.address).fee_last_change
        > last_change
    )

    # Make sure the default is not changed.
    assert vault_factory.protocol_fee_config().fee_recipient == gov.address
    assert vault_factory.protocol_fee_config().fee_bps == 0
    assert vault_factory.protocol_fee_config().fee_last_change == last_change


def test__remove_custom_protocol_fee(gov, vault_factory, create_vault, asset):
    # Set the default protocol fee recipient
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    generic_fee = int(8)
    vault_factory.set_protocol_fee_bps(generic_fee, sender=gov)

    last_change = vault_factory.protocol_fee_config().fee_last_change

    vault = create_vault(asset)

    new_fee = int(20)
    # Set custom fee for new vault.
    tx = vault_factory.set_custom_protocol_fee_bps(vault.address, new_fee, sender=gov)

    event = list(tx.decode_logs(vault_factory.UpdateCustomProtocolFee))

    assert len(event) == 1
    assert event[0].vault == vault.address
    assert event[0].new_custom_protocol_fee == new_fee

    # Should now be different than default
    assert (
        vault_factory.protocol_fee_config(sender=vault.address).fee_recipient
        == gov.address
    )
    assert vault_factory.protocol_fee_config(sender=vault.address).fee_bps == new_fee
    assert (
        vault_factory.protocol_fee_config(sender=vault.address).fee_last_change
        > last_change
    )

    # Now remove the custom fee config
    tx = vault_factory.remove_custom_protocol_fee(vault.address, sender=gov)

    event = list(tx.decode_logs(vault_factory.RemovedCustomProtocolFee))

    len(event) == 1
    assert event[0].vault == vault.address

    # Should now be the default
    assert (
        vault_factory.protocol_fee_config(sender=vault.address).fee_recipient
        == gov.address
    )
    assert (
        vault_factory.protocol_fee_config(sender=vault.address).fee_bps == generic_fee
    )
    assert (
        vault_factory.protocol_fee_config(sender=vault.address).fee_last_change
        == last_change
    )

    assert (
        vault_factory.custom_protocol_fee_config(vault.address).fee_recipient
        == ZERO_ADDRESS
    )
    assert vault_factory.custom_protocol_fee_config(vault.address).fee_bps == 0
    assert vault_factory.custom_protocol_fee_config(vault.address).fee_last_change == 0


def test__set_custom_protocol_fee_by_bunny__reverts(
    bunny, vault_factory, create_vault, asset
):
    vault = create_vault(asset)
    with ape.reverts("not governance"):
        vault_factory.set_custom_protocol_fee_bps(vault.address, 10, sender=bunny)


def test__set__custom_protocol_fees_too_high__reverts(
    gov, vault_factory, create_vault, asset
):
    vault = create_vault(asset)
    with ape.reverts("fee too high"):
        vault_factory.set_custom_protocol_fee_bps(vault.address, 26, sender=gov)


def test__remove_custom_protocol_fee_by_bunny__reverts(
    bunny, vault_factory, create_vault, asset
):
    vault = create_vault(asset)
    with ape.reverts("not governance"):
        vault_factory.remove_custom_protocol_fee(vault, sender=bunny)


def test__set_protocol_fee_recipient_by_bunny__reverts(bunny, vault_factory):
    with ape.reverts("not governance"):
        vault_factory.set_protocol_fee_recipient(bunny.address, sender=bunny)


def test__set_protocol_fees_too_high__reverts(gov, vault_factory):
    with ape.reverts("fee too high"):
        vault_factory.set_protocol_fee_bps(26, sender=gov)


def test__set_protocol_fees_by_bunny__reverts(bunny, vault_factory):
    with ape.reverts("not governance"):
        vault_factory.set_protocol_fee_bps(20, sender=bunny)
