# Copyright (c) 2010-2017 Guilherme Gondim. All rights reserved.
# Copyright (c) 2009 Simon Willison. All rights reserved.
# Copyright (c) 2002 Drew Perttula. All rights reserved.
#
# License:
#   Python Software Foundation License version 2
#
# See the file "LICENSE" for terms & conditions for usage, and a DISCLAIMER OF
# ALL WARRANTIES.
#
# This Baseconv distribution contains no GNU General Public Licensed (GPLed)
# code so it may be used in proprietary projects just like prior ``baseconv``
# distributions.
#
# All trademarks referenced herein are property of their respective holders.
#

"""
Convert numbers from base 10 integers to base X strings and back again.

Example usage::

  >>> from baseconv import base2, base16, base36, base56, base58, base62, base64
  >>> base2.encode(1234)
  '10011010010'
  >>> base2.decode('10011010010')
  '1234'
  >>> base64.encode(100000000000000000000000000000000000L)
  '4q9XSiTDWYk7Z-W00000'
  >>> base64.decode('4q9XSiTDWYk7Z-W00000')
  '100000000000000000000000000000000000'

  >>> from baseconv import BaseConverter
  >>> myconv = BaseConverter('MyOwnAlphabet0123456')
  >>> repr(myconv)
  "BaseConverter('MyOwnAlphabet0123456', sign='-')"
  >>> myconv.encode('1234')
  'wy1'
  >>> myconv.decode('wy1')
  '1234'
  >>> myconv.encode(-1234)
  '-wy1'
  >>> myconv.decode('-wy1')
  '-1234'
  >>> altsign = BaseConverter('abcd-', sign='$')
  >>> repr(altsign)
  "BaseConverter('abcd-', sign='$')"
  >>> altsign.encode(-1000000)
  '$cc-aaaaaa'
  >>> altsign.decode('$cc-aaaaaa')
  '-1000000'

Exceptions::

  >>> BaseConverter('')
  Traceback (most recent call last):
      ...
  ValueError: converter base digits length too short

  >>> BaseConverter(digits='xyz-._', sign='-')
  Traceback (most recent call last):
      ...
  ValueError: sign character found in converter base digits

  >>> base56.encode(3.14)
  Traceback (most recent call last):
      ...
  ValueError: invalid digit "."

  >>> base58.decode('0IOl')
  Traceback (most recent call last):
      ...
  ValueError: invalid digit "0"

"""

__version__ = '1.2.2'

BASE2_ALPHABET = '01'
BASE16_ALPHABET = '0123456789ABCDEF'
BASE36_ALPHABET = '0123456789abcdefghijklmnopqrstuvwxyz'
BASE56_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz'
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
BASE62_ALPHABET = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
BASE64_ALPHABET = BASE62_ALPHABET + '-_'


class BaseConverter(object):
    decimal_digits = '0123456789'

    def __init__(self, digits, sign='-'):
        self.sign = sign
        self.digits = digits
        if sign in self.digits:
            raise ValueError('sign character found in converter base digits')
        if len(self.digits) <= 1:
            raise ValueError('converter base digits length too short')

    def __repr__(self):
        data = (self.__class__.__name__, self.digits, self.sign)
        return "%s(%r, sign=%r)" % data

    def _convert(self, number, from_digits, to_digits):
        # make an integer out of the number
        x = 0
        for digit in str(number):
            try:
                x = x * len(from_digits) + from_digits.index(digit)
            except ValueError:
                raise ValueError('invalid digit "%s"' % digit)

        # create the result in base 'len(to_digits)'
        if x == 0:
            res = to_digits[0]
        else:
            res = ''
            while x > 0:
                digit = x % len(to_digits)
                res = to_digits[digit] + res
                x = int(x // len(to_digits))
        return res

    def encode(self, number):
        if str(number)[0] == '-':
            neg = True
            number = str(number)[1:]
        else:
            neg = False

        value = self._convert(number, self.decimal_digits, self.digits)
        if neg:
            return self.sign + value
        return value

    def decode(self, number):
        if str(number)[0] == self.sign:
            neg = True
            number = str(number)[1:]
        else:
            neg = False

        value = self._convert(number, self.digits, self.decimal_digits)
        if neg:
            return '-' + value
        return value


base2 = BaseConverter(BASE2_ALPHABET)
base16 = BaseConverter(BASE16_ALPHABET)
base36 = BaseConverter(BASE36_ALPHABET)
base56 = BaseConverter(BASE56_ALPHABET)
base58 = BaseConverter(BASE58_ALPHABET)
base62 = BaseConverter(BASE62_ALPHABET)
base64 = BaseConverter(BASE64_ALPHABET, sign='$')


if __name__ == '__main__':
    # doctests
    import doctest
    doctest.testmod()

    # other tests
    nums = [-10 ** 10, 10 ** 10] + list(range(-100, 100))
    for converter in [base2, base16, base36, base56, base58, base62, base64]:
        for i in nums:
            assert i == int(converter.decode(converter.encode(i))), '%s failed' % i
