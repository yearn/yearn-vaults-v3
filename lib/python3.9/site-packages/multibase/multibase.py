from collections import namedtuple
from morphys import ensure_bytes

from .converters import BaseStringConverter, Base16StringConverter, IdentityConverter, Base64StringConverter, \
    Base32StringConverter

Encoding = namedtuple('Encoding', 'encoding,code,converter')
CODE_LENGTH = 1
ENCODINGS = [
    Encoding('identity', b'\x00', IdentityConverter()),
    Encoding('base2', b'0', BaseStringConverter('01')),
    Encoding('base8', b'7', BaseStringConverter('01234567')),
    Encoding('base10', b'9', BaseStringConverter('0123456789')),
    Encoding('base16', b'f', Base16StringConverter('0123456789abcdef')),
    Encoding('base32hex', b'v', Base32StringConverter('0123456789abcdefghijklmnopqrstuv')),
    Encoding('base32', b'b', Base32StringConverter('abcdefghijklmnopqrstuvwxyz234567')),
    Encoding('base32z', b'h', BaseStringConverter('ybndrfg8ejkmcpqxot1uwisza345h769')),
    Encoding('base36', b'k', BaseStringConverter('0123456789abcdefghijklmnopqrstuvwxyz')),
    Encoding('base36upper', b'K', BaseStringConverter('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')),
    Encoding('base58flickr', b'Z', BaseStringConverter('123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ')),
    Encoding('base58btc', b'z', BaseStringConverter('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')),
    Encoding('base64', b'm', Base64StringConverter('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/')),
    Encoding('base64url', b'u',
             Base64StringConverter(
                 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'),
             ),
]

ENCODINGS_LOOKUP = {}
for codec in ENCODINGS:
    ENCODINGS_LOOKUP[codec.encoding] = codec
    ENCODINGS_LOOKUP[codec.code] = codec


def encode(encoding, data):
    """
    Encodes the given data using the encoding that is specified

    :param str encoding: encoding to use, should be one of the supported encoding
    :param data: data to encode
    :type data: str or bytes
    :return: multibase encoded data
    :rtype: bytes
    :raises ValueError: if the encoding is not supported
    """
    data = ensure_bytes(data, 'utf8')
    try:
        return ENCODINGS_LOOKUP[encoding].code + ENCODINGS_LOOKUP[encoding].converter.encode(data)
    except KeyError:
        raise ValueError('Encoding {} not supported.'.format(encoding))


def get_codec(data):
    """
    Returns the codec used to encode the given data

    :param data: multibase encoded data
    :type data: str or bytes
    :return: the :py:obj:`multibase.Encoding` object for the data's codec
    :raises ValueError: if the codec is not supported
    """
    try:
        key = ensure_bytes(data[:CODE_LENGTH], 'utf8')
        codec = ENCODINGS_LOOKUP[key]
    except KeyError:
        raise ValueError('Can not determine encoding for {}'.format(data))
    else:
        return codec


def is_encoded(data):
    """
    Checks if the given data is encoded or not

    :param data: multibase encoded data
    :type data: str or bytes
    :return: if the data is encoded or not
    :rtype: bool
    """
    try:
        get_codec(data)
        return True
    except ValueError:
        return False


def decode(data):
    """
    Decode the multibase decoded data
    :param data: multibase encoded data
    :type data: str or bytes
    :return: decoded data
    :rtype: str
    :raises ValueError: if the data is not multibase encoded
    """
    data = ensure_bytes(data, 'utf8')
    codec = get_codec(data)
    return codec.converter.decode(data[CODE_LENGTH:])
