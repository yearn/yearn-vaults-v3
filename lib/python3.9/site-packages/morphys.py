# coding: utf8

# Copyright 2016 Michał Kaliński

"""
Utilities for easy and smart conversions between unicode and bytes.
"""

import sys


__all__ = (
    'ensure_bytes',
    'ensure_unicode',
    'StrMorpher',
)


if sys.version_info.major > 2:
    _bytes_type = bytes
    _unicode_type = str
else:
    _bytes_type = str
    _unicode_type = unicode

#: The encoding used by default by utilities in this module.
default_encoding = 'utf-8'


def ensure_bytes(obj, encoding=None):
    """
    Convert ``obj`` to a byte string, if it isn't one already.

    The conversion method is as follows:

    1. If ``obj`` is a byte string, return it unchanged.
    2. If ``obj`` is an unicode string, encode it using ``encoding``.
    3. Otherwise, cast ``obj`` to unicode string and encode it using
       ``encoding``.

    If ``encoding`` is ``None``, the default encoding will be used.
    """

    if isinstance(obj, _bytes_type):
        return obj

    enc = encoding or default_encoding

    if isinstance(obj, _unicode_type):
        return obj.encode(enc)

    return _unicode_type(obj).encode(enc)


def ensure_unicode(obj, encoding=None):
    """
    Convert ``obj`` to an unicode string, if it isn't one already.

    The conversion method is as follows:

    1. If ``obj`` is an unicode string, return it unchanged.
    2. If ``obj`` is a byte string, decode it using ``encoding``.
    3. Otherwise, cat ``obj`` to unicode string.

    If ``encoding`` is ``None``, the default encoding will be used.
    """

    if isinstance(obj, _unicode_type):
        return obj

    if isinstance(obj, _bytes_type):
        return obj.decode(encoding or default_encoding)

    return _unicode_type(obj)


class StrMorpher(object):
    """
    Wrapper which will return its underlying object as an unicode or byte
    string when required.

    ``ensure_unicode`` or ``ensure_bytes`` are used to convert ``obj`` when
    the respective "magic" methods (``__unicode__`` / ``__str__`` or
    ``__str__`` / ``__bytes__``) are called. The class doesn't provide any
    non-magic methods.

    If the ``encoding`` parameter is ``None``, the default value is captured
    at the moment when ``MorphStr`` is constructed.
    This is for consistency with cases when encoding is explicitly passed
    (since its value cannot change after object creation).

    ``StrMorpher`` objects are hashable and can be compared for equality.
    A ``StrMorpher`` is equal to another ``StrMorpher`` if its ``obj`` and
    (effective) ``encoding`` parameters are equal.
    """

    __slots__ = '_obj', '_enc'

    def __init__(self, obj, encoding=None):
        self._obj = obj
        self._enc = encoding or default_encoding

    def __repr__(self):
        return '{}({!r}, encoding={!r})'.format(
            self.__class__.__name__,
            self._obj,
            self._enc,
        )

    def __hash__(self):
        return hash((self._obj, self._enc))

    def __eq__(self, other):
        return (isinstance(other, StrMorpher) and
                self._obj == other._obj and
                self._enc == other._enc)

    def __ne__(self, other):
        return not (self == other)

    def _to_bytes(self):
        return ensure_bytes(self._obj, self._enc)

    def _to_unicode(self):
        return ensure_unicode(self._obj, self._enc)

    if sys.version_info.major > 2:
        __str__ = _to_unicode
        __bytes__ = _to_bytes
    else:
        __str__ = _to_bytes
        __unicode__ = _to_unicode
