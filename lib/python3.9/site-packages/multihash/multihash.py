# -*- coding: utf-8 -*-
from binascii import hexlify
from collections import namedtuple
from io import BytesIO

import base58
import varint

import multihash.constants as constants


Multihash = namedtuple('Multihash', 'code,name,length,digest')


def to_hex_string(multihash):
    """
    Convert the given multihash to a hex encoded string

    :param bytes hash: the multihash to be converted to hex string
    :return: input multihash in str
    :rtype: str
    :raises: `TypeError`, if the `multihash` has incorrect type
    """
    if not isinstance(multihash, bytes):
        raise TypeError('multihash should be bytes, not {}'.format(type(multihash)))

    return hexlify(multihash).decode()


def from_hex_string(multihash):
    """
    Convert the given hex encoded string to a multihash

    :param str multihash: hex multihash encoded string
    :return: input multihash in bytes
    :rtype: bytes
    :raises: `TypeError`, if the `multihash` has incorrect type
    """
    if not isinstance(multihash, str):
        raise TypeError('multihash should be str, not {}'.format(type(multihash)))

    return bytes.fromhex(multihash)


def to_b58_string(multihash):
    """
    Convert the given multihash to a base58 encoded string

    :param bytes multihash: multihash to base58 encode
    :return: base58 encoded multihash string
    :rtype: str
    :raises: `TypeError`, if the `multihash` has incorrect type
    """
    if not isinstance(multihash, bytes):
        raise TypeError('multihash should be bytes, not {}'.format(type(multihash)))

    return base58.b58encode(multihash).decode()


def from_b58_string(multihash):
    """
    Convert the given base58 encoded string to a multihash

    :param str multihash: base58 encoded multihash string
    :return: decoded multihash
    :rtype: bytes
    :raises: `TypeError`, if the `multihash` has incorrect type
    """
    if not isinstance(multihash, str):
        raise TypeError('multihash should be str, not {}'.format(type(multihash)))

    return base58.b58decode(multihash)


def is_app_code(code):
    """
    Checks whether a code is part of the app range

    :param int code: input code
    :return: if `code` is in the app range or not
    :rtype: bool
    """
    return 0 < code < 0x10


def coerce_code(hash_fn):
    """
    Converts a hash function name into its code

    If passed a number it will return the number if it's a valid code

    :param hash_fn: The input hash function can be
        - str, the name of the hash function
        - int, the code of the hash function
    :return: hash function code
    :rtype: int
    :raises ValueError: if the hash function is not supported
    :raises ValueError: if the hash code is not supported
    :raises ValueError: if the hash type is not a string or an int
    """
    if isinstance(hash_fn, str):
        try:
            return constants.HASH_CODES[hash_fn]
        except KeyError:
            raise ValueError('Unsupported hash function {}'.format(hash_fn))

    elif isinstance(hash_fn, int):
        if hash_fn in constants.CODE_HASHES or is_app_code(hash_fn):
            return hash_fn
        raise ValueError('Unsupported hash code {}'.format(hash_fn))

    raise TypeError('hash code should be either an integer or a string')


def is_valid_code(code):
    """
    Checks whether a multihash code is valid or not

    :param int code: input code
    :return: if the code valid or not
    :rtype: bool
    """
    return is_app_code(code) or code in constants.CODE_HASHES


def decode(multihash):
    """
    Decode a hash from the given multihash

    :param bytes multihash: multihash
    :return: decoded :py:class:`multihash.Multihash` object
    :rtype: :py:class:`multihash.Multihash`
    :raises TypeError: if `multihash` is not of type `bytes`
    :raises ValueError: if the length of multihash is less than 3 characters
    :raises ValueError: if the code is invalid
    :raises ValueError: if the length is invalid
    :raises ValueError: if the length is not same as the digest
    """
    if not isinstance(multihash, bytes):
        raise TypeError('multihash should be bytes, not {}', type(multihash))

    if len(multihash) < 3:
        raise ValueError('multihash must be greater than 3 bytes.')

    buffer = BytesIO(multihash)
    try:
        code = varint.decode_stream(buffer)
    except TypeError:
        raise ValueError('Invalid varint provided')

    if not is_valid_code(code):
        raise ValueError('Unsupported hash code {}'.format(code))

    try:
        length = varint.decode_stream(buffer)
    except TypeError:
        raise ValueError('Invalid length provided')

    buf = buffer.read()

    if len(buf) != length:
        raise ValueError('Inconsistent multihash length {} != {}'.format(len(buf), length))

    return Multihash(code=code, name=constants.CODE_HASHES.get(code, code), length=length, digest=buf)


def encode(digest, code, length=None):
    """
    Encode a hash digest along with the specified function code

    :param bytes digest: hash digest
    :param (int or str) code: hash function code
    :param int length: hash digest length
    :return: encoded multihash
    :rtype: bytes
    :raises TypeError: when the digest is not a bytes object
    :raises ValueError: when the digest length is not correct
    """
    hash_code = coerce_code(code)

    if not isinstance(digest, bytes):
        raise TypeError('digest must be a bytes object, not {}'.format(type(digest)))

    if length is None:
        length = len(digest)

    elif length != len(digest):
        raise ValueError('digest length should be equal to specified length')

    return varint.encode(hash_code) + varint.encode(length) + digest


def is_valid(multihash):
    """
    Check if the given buffer is a valid multihash

    :param bytes multihash: input multihash
    :return: if the input is a valid multihash or not
    :rtype: bool
    """
    try:
        decode(multihash)
        return True
    except ValueError:
        return False


def get_prefix(multihash):
    """
    Return the prefix from the multihash

    :param bytes multihash: input multihash
    :return: multihash prefix
    :rtype: bytes
    :raises ValueError: when the multihash is invalid
    """
    if is_valid(multihash):
        return multihash[:2]

    raise ValueError('invalid multihash')
