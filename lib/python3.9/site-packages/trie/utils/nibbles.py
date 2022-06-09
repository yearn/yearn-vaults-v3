import itertools

from eth_utils import (
    to_tuple,
)
from eth_utils.toolz import (
    partition,
)

from trie.constants import (
    NIBBLE_TERMINATOR,
    HP_FLAG_2,
    HP_FLAG_0,
)
from trie.exceptions import (
    InvalidNibbles,
)


NIBBLES_LOOKUPS = {
    byte: (byte >> 4, byte & 15)
    for byte
    in range(256)
}


def _bytes_to_nibbles(value):
    """
    Convert a byte string to nibbles
    """
    for byte in value:
        yield from NIBBLES_LOOKUPS[byte]


def bytes_to_nibbles(value):
    return tuple(_bytes_to_nibbles(value))


VALID_NIBBLES = set(range(16))
REVERSE_NIBBLES_LOOKUP = {
    value: key
    for key, value
    in NIBBLES_LOOKUPS.items()
}


def nibbles_to_bytes(nibbles):
    if any(nibble not in VALID_NIBBLES for nibble in nibbles):
        raise InvalidNibbles(
            "Nibbles contained invalid value.  Must be constrained between [0, 15]"
        )

    if len(nibbles) % 2:
        raise InvalidNibbles("Nibbles must be even in length")

    value = bytes(REVERSE_NIBBLES_LOOKUP[pair] for pair in partition(2, nibbles))
    return value


def is_nibbles_terminated(nibbles):
    return nibbles and nibbles[-1] == NIBBLE_TERMINATOR


@to_tuple
def add_nibbles_terminator(nibbles):
    if is_nibbles_terminated(nibbles):
        return nibbles
    return itertools.chain(nibbles, (NIBBLE_TERMINATOR,))


@to_tuple
def remove_nibbles_terminator(nibbles):
    if is_nibbles_terminated(nibbles):
        return nibbles[:-1]
    return nibbles


def encode_nibbles(nibbles):
    """
    The Hex Prefix function
    """
    if is_nibbles_terminated(nibbles):
        flag = HP_FLAG_2
    else:
        flag = HP_FLAG_0

    raw_nibbles = remove_nibbles_terminator(nibbles)

    is_odd = len(raw_nibbles) % 2

    if is_odd:
        flagged_nibbles = tuple(itertools.chain(
            (flag + 1,),
            raw_nibbles,
        ))
    else:
        flagged_nibbles = tuple(itertools.chain(
            (flag, 0),
            raw_nibbles,
        ))

    prefixed_value = nibbles_to_bytes(flagged_nibbles)

    return prefixed_value


def decode_nibbles(value):
    """
    The inverse of the Hex Prefix function
    """
    nibbles_with_flag = bytes_to_nibbles(value)
    flag = nibbles_with_flag[0]

    needs_terminator = flag in {HP_FLAG_2, HP_FLAG_2 + 1}
    is_odd_length = flag in {HP_FLAG_0 + 1, HP_FLAG_2 + 1}

    if is_odd_length:
        raw_nibbles = nibbles_with_flag[1:]
    else:
        raw_nibbles = nibbles_with_flag[2:]

    if needs_terminator:
        nibbles = add_nibbles_terminator(raw_nibbles)
    else:
        nibbles = raw_nibbles

    return nibbles
