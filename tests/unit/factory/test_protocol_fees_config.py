import ape
from ape import chain
from utils.constants import ZERO_ADDRESS


def test__set_protocol_fee_recipient(gov, vault_factory):
    tx = vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    event = list(tx.decode_logs(vault_factory.UpdateProtocolFeeRecipient))
    assert event[0].old_fee_recipient == ZERO_ADDRESS
    assert event[0].new_fee_recipient == gov.address

    assert vault_factory.protocol_fee_config()[1] == gov.address


def test__set_protocol_fee_recipient__zero_address__reverts(gov, vault_factory):
    with ape.reverts("zero address"):
        vault_factory.set_protocol_fee_recipient(ZERO_ADDRESS, sender=gov)


def test__set_protocol_fees(gov, vault_factory):
    assert vault_factory.protocol_fee_config()[0] == 0

    # Need to set the fee recipient first
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    tx = vault_factory.set_protocol_fee_bps(20, sender=gov)

    event = list(tx.decode_logs(vault_factory.UpdateProtocolFeeBps))
    assert event[0].old_fee_bps == 0
    assert event[0].new_fee_bps == 20

    assert vault_factory.protocol_fee_config()[0] == 20


def test__set_custom_protocol_fee(gov, vault_factory, create_vault, asset):
    # Set the default protocol fee recipient
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    assert vault_factory.protocol_fee_config() == (0, gov.address)

    vault = create_vault(asset)

    # Make sure its currently set to the default settings.
    assert vault_factory.protocol_fee_config(vault.address) == (0, gov.address)
    assert vault_factory.protocol_fee_config(sender=vault.address) == (0, gov.address)

    new_fee = int(20)
    # Set custom fee for new vault.
    tx = vault_factory.set_custom_protocol_fee_bps(vault.address, new_fee, sender=gov)

    event = list(tx.decode_logs(vault_factory.UpdateCustomProtocolFee))

    assert len(event) == 1
    assert event[0].vault == vault.address
    assert event[0].new_custom_protocol_fee == new_fee

    assert vault_factory.use_custom_protocol_fee(vault.address) == True
    assert vault_factory.protocol_fee_config(vault.address)[0] == new_fee

    # Should now be different than default
    assert vault_factory.protocol_fee_config(vault.address) == (new_fee, gov.address)
    assert vault_factory.protocol_fee_config(sender=vault.address) == (
        new_fee,
        gov.address,
    )

    # Make sure the default is not changed.
    assert vault_factory.protocol_fee_config() == (0, gov.address)


def test__remove_custom_protocol_fee(gov, vault_factory, create_vault, asset):
    # Set the default protocol fee recipient
    vault_factory.set_protocol_fee_recipient(gov.address, sender=gov)

    generic_fee = int(8)
    vault_factory.set_protocol_fee_bps(generic_fee, sender=gov)

    vault = create_vault(asset)

    new_fee = int(20)
    # Set custom fee for new vault.
    tx = vault_factory.set_custom_protocol_fee_bps(vault.address, new_fee, sender=gov)

    event = list(tx.decode_logs(vault_factory.UpdateCustomProtocolFee))

    assert len(event) == 1
    assert event[0].vault == vault.address
    assert event[0].new_custom_protocol_fee == new_fee

    # Should now be different than default
    assert vault_factory.protocol_fee_config(vault.address) == (new_fee, gov.address)
    assert vault_factory.protocol_fee_config(sender=vault.address) == (
        new_fee,
        gov.address,
    )

    # Now remove the custom fee config
    tx = vault_factory.remove_custom_protocol_fee(vault.address, sender=gov)

    event = list(tx.decode_logs(vault_factory.RemovedCustomProtocolFee))

    len(event) == 1
    assert event[0].vault == vault.address

    # Should now be the default
    assert vault_factory.protocol_fee_config(vault.address) == (
        generic_fee,
        gov.address,
    )
    assert vault_factory.protocol_fee_config(sender=vault.address) == (
        generic_fee,
        gov.address,
    )

    assert vault_factory.use_custom_protocol_fee(vault.address) == False


def test__set_protocol_fee_before_recipient__reverts(gov, vault_factory):
    assert vault_factory.protocol_fee_config()[1] == ZERO_ADDRESS

    with ape.reverts("no recipient"):
        vault_factory.set_protocol_fee_bps(20, sender=gov)


def test__set_custom_fee_before_recipient__reverts(gov, vault_factory, vault):
    assert vault_factory.protocol_fee_config()[1] == ZERO_ADDRESS

    with ape.reverts("no recipient"):
        vault_factory.set_custom_protocol_fee_bps(vault.address, 20, sender=gov)


def test__set_custom_protocol_fee_by_bunny__reverts(
    bunny, vault_factory, create_vault, asset
):
    vault = create_vault(asset, vault_name="new vault")
    with ape.reverts("not governance"):
        vault_factory.set_custom_protocol_fee_bps(vault.address, 10, sender=bunny)


def test__set__custom_protocol_fees_too_high__reverts(
    gov, vault_factory, create_vault, asset
):
    vault = create_vault(asset, vault_name="new vault")
    with ape.reverts("fee too high"):
        vault_factory.set_custom_protocol_fee_bps(vault.address, 5_001, sender=gov)


def test__remove_custom_protocol_fee_by_bunny__reverts(
    bunny, vault_factory, create_vault, asset
):
    vault = create_vault(asset, vault_name="new vault")
    with ape.reverts("not governance"):
        vault_factory.remove_custom_protocol_fee(vault, sender=bunny)


def test__set_protocol_fee_recipient_by_bunny__reverts(bunny, vault_factory):
    with ape.reverts("not governance"):
        vault_factory.set_protocol_fee_recipient(bunny.address, sender=bunny)


def test__set_protocol_fees_too_high__reverts(gov, vault_factory):
    with ape.reverts("fee too high"):
        vault_factory.set_protocol_fee_bps(10_001, sender=gov)


def test__set_protocol_fees_by_bunny__reverts(bunny, vault_factory):
    with ape.reverts("not governance"):
        vault_factory.set_protocol_fee_bps(20, sender=bunny)
