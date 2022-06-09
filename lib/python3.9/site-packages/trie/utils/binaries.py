from eth_utils import (
    apply_to_return_value,
)
from eth_utils.toolz import (
    partition_all,
)


from trie.constants import (
    EXP,
    TWO_BITS,
    PREFIX_00,
    PREFIX_100000,
)


@apply_to_return_value(bytes)
def decode_from_bin(input_bin):
    """
    0100000101010111010000110100100101001001 -> ASCII
    """
    for chunk in partition_all(8, input_bin):
        yield sum(
            2**exp * bit
            for exp, bit
            in enumerate(reversed(chunk))
        )


@apply_to_return_value(bytes)
def encode_to_bin(value):
    """
    ASCII -> 0100000101010111010000110100100101001001
    """
    for char in value:
        for exp in EXP:
            if char & exp:
                yield True
            else:
                yield False


def encode_from_bin_keypath(input_bin):
    """
    Encodes a sequence of 0s and 1s into tightly packed bytes
    Used in encoding key path of a KV-NODE
    """
    padded_bin = bytes((4 - len(input_bin)) % 4) + input_bin
    prefix = TWO_BITS[len(input_bin) % 4]
    if len(padded_bin) % 8 == 4:
        return decode_from_bin(PREFIX_00 + prefix + padded_bin)
    else:
        return decode_from_bin(PREFIX_100000 + prefix + padded_bin)


def decode_to_bin_keypath(path):
    """
    Decodes bytes into a sequence of 0s and 1s
    Used in decoding key path of a KV-NODE
    """
    path = encode_to_bin(path)
    if path[0] == 1:
        path = path[4:]
    assert path[0:2] == PREFIX_00
    padded_len = TWO_BITS.index(path[2:4])
    return path[4+((4 - padded_len) % 4):]
