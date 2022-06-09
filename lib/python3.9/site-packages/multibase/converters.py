from io import BytesIO
from itertools import zip_longest

from baseconv import BaseConverter
from morphys import ensure_bytes


class BaseStringConverter(BaseConverter):
    def encode(self, bytes):
        number = int.from_bytes(bytes, byteorder='big', signed=False)
        return ensure_bytes(super(BaseStringConverter, self).encode(number))

    def bytes_to_int(self, bytes):
        length = len(bytes)
        base = len(self.digits)
        value = 0

        for i, x in enumerate(bytes):
            value += self.digits.index(chr(x)) * base ** (length - (i + 1))
        return value

    def decode(self, bytes):
        decoded_int = self.bytes_to_int(bytes)
        # See https://docs.python.org/3.5/library/stdtypes.html#int.to_bytes for more about the magical expression
        # below
        decoded_data = decoded_int.to_bytes((decoded_int.bit_length() + 7) // 8, byteorder='big')
        return decoded_data


class Base16StringConverter(BaseStringConverter):
    def encode(self, bytes):
        return ensure_bytes(''.join(['{:02x}'.format(byte) for byte in bytes]))


class BaseByteStringConverter(object):
    ENCODE_GROUP_BYTES = 1
    ENCODING_BITS = 1
    DECODING_BITS = 1

    def __init__(self, digits):
        self.digits = digits

    def _chunk_with_padding(self, iterable, n, fillvalue=None):
        "Collect data into fixed-length chunks or blocks"
        # _chunk_with_padding('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        return zip_longest(*args, fillvalue=fillvalue)

    def _chunk_without_padding(self, iterable, n):
        return map(''.join, zip(*[iter(iterable)] * n))

    def _encode_bytes(self, bytes_, group_bytes, encoding_bits, decoding_bits):
        buffer = BytesIO(bytes_)
        encoded_bytes = BytesIO()
        while True:
            byte_ = buffer.read(group_bytes)
            if not byte_:
                break

            # convert all bytes to a binary format and concatenate them into a 24bit string
            binstringfmt = '{{:0{}b}}'.format(encoding_bits)
            binstring = ''.join([binstringfmt.format(x) for x in byte_])
            # break the 24 bit length string into pieces of 6 bits each and convert them to integer
            digits = (int(''.join(x), 2) for x in self._chunk_with_padding(binstring, decoding_bits, '0'))

            for digit in digits:
                # convert binary representation to an integer
                encoded_bytes.write(ensure_bytes(self.digits[digit]))

        return encoded_bytes.getvalue()

    def _decode_bytes(self, bytes_, group_bytes, decoding_bits, encoding_bits):
        buffer = BytesIO()
        decoded_bytes = BytesIO()

        for byte_ in bytes_.decode():
            idx = self.digits.index(byte_)
            buffer.write(bytes([idx]))

        buffer.seek(0)
        while True:
            byte_ = buffer.read(group_bytes)
            if not byte_:
                break

            # convert all bytes to a binary format and concatenate them into a 8, 16, 24bit string
            binstringfmt = '{{:0{}b}}'.format(decoding_bits)
            binstring = ''.join([binstringfmt.format(x) for x in byte_])

            # break the 24 bit length string into pieces of 8 bits each and convert them to integer
            digits = [int(''.join(x), 2) for x in self._chunk_without_padding(binstring, encoding_bits)]

            for digit in digits:
                decoded_bytes.write(bytes([digit]))

        return decoded_bytes.getvalue()

    def encode(self, bytes):
        raise NotImplementedError

    def decode(self, bytes):
        return NotImplementedError


class Base64StringConverter(BaseByteStringConverter):
    def encode(self, bytes):
        return self._encode_bytes(ensure_bytes(bytes), 3, 8, 6)

    def decode(self, bytes):
        return self._decode_bytes(ensure_bytes(bytes), 4, 6, 8)


class Base32StringConverter(BaseByteStringConverter):
    def encode(self, bytes):
        return self._encode_bytes(ensure_bytes(bytes), 5, 8, 5)

    def decode(self, bytes):
        return self._decode_bytes(ensure_bytes(bytes), 8, 5, 8)


class IdentityConverter(object):
    def encode(self, x):
        return x

    def decode(self, x):
        return x
