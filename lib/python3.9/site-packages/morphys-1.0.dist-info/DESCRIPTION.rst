=======
Morphys
=======

**Morphys** is a simple, small library providing utilities for easy smart
conversions between ``unicode`` and ``bytes`` types.

In Python 2, the treatment of ``unicode`` and ``bytes`` objects is a potential
source of many surprising and annoying errors, should a non-ASCII character
appear anywhere in a string.

The two types are completely equivalent if only ASCII characters are used, and
many libraries treat them as such, while others are more vigilant about which
type they accept. Some can even return one or the other type of string from the
same function depending on the content (for example, the standard library
``json`` module).

**Morphys** is meant to help with cases where types of strings handled by
libraries are inconsistent or undocumented. Or where simply both types of
string can appear, but should be coerced to the same type before being handled.


Conversion functions
====================

**Morphys** provides two functions for smart conversions to ``unicode`` or
``bytes``. They just return their argument unchanged if it's already the right
type and can also convert any object defining the ``__unicode__`` (or
``__str__`` in Python 3) "magic" method.

``ensure_bytes(obj, encoding=None)``
    Return ``obj`` as a ``bytes`` object, if necessary encoding it using
    ``encoding``.

``ensure_unicode(obj, encoding=None)``
    Return ``obj`` as an ``unicode`` object, if necessary decoding it using
    ``encoding``.

See docstrings in the module for more detailed description of the functions.


Lazy conversion wrapper
=======================

In certain cases it may be more convenient to use an object that can be used
both as ``bytes`` or ``unicode`` as needed. The class ``StrMorpher`` is
provided for this case. Its constructor takes the same arguments as the
conversion functions. The object makes calls to the appropriate conversion
function when its "magic" methods that convert to ``bytes`` or ``unicode``
are invoked.

Note, that ``StrMorpher`` is not itself a subclass of any of the string
types and relies on the "magic" methods being called to produce the actual
string objects.

See docstrings in the module for more detailed description of the class.


Default encoding
================

The ``encoding`` parameter is optional in all places where it's accepted. Where
it is left as ``None``, the default encoding is used.

The default encoding is controlled by ``default_encoding`` global
variable in the ``morphys`` module. Initially it's set to "utf-8", but it's
allowed to set it to a different encoding name from user code.


Python 3
========

While **Morphys** is mostly meant to solve issues of string types handling in
Python 2, it's fully compatible with Python 3 and can be used with it.


