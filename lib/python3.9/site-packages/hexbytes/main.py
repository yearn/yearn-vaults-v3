from typing import (
    Type,
    Union,
    cast,
    overload,
)

from ._utils import (
    to_bytes,
)


class HexBytes(bytes):
    """
    HexBytes is a *very* thin wrapper around the python built-in :class:`bytes` class.

    It has these three changes:
        1. Accepts more initializing values, like hex strings, non-negative integers, and booleans
        2. Returns hex with prefix '0x' from :meth:`HexBytes.hex`
        3. The representation at console is in hex
    """
    def __new__(cls: Type[bytes], val: Union[bool, bytearray, bytes, int, str]) -> "HexBytes":
        bytesval = to_bytes(val)
        return cast(HexBytes, super().__new__(cls, bytesval))  # type: ignore  # https://github.com/python/typeshed/issues/2630  # noqa: E501

    def hex(self) -> str:
        """
        Output hex-encoded bytes, with an "0x" prefix.

        Everything following the "0x" is output exactly like :meth:`bytes.hex`.
        """
        return '0x' + super().hex()

    @overload
    def __getitem__(self, key: int) -> int:
        ...

    @overload  # noqa: F811
    def __getitem__(self, key: slice) -> 'HexBytes':
        ...

    def __getitem__(self, key: Union[int, slice]) -> Union[int, bytes, 'HexBytes']:  # noqa: F811
        result = super().__getitem__(key)
        if hasattr(result, 'hex'):
            return type(self)(result)
        else:
            return result

    def __repr__(self) -> str:
        return f"HexBytes({self.hex()!r})"
