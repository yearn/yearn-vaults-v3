from typing import Any, no_type_check

from pydantic import BaseModel as _BaseModel

from .utils import HexBytes


class BaseModel(_BaseModel):
    def dict(self, *args, **kwargs) -> dict:
        # NOTE: We do this to accomodate the aliases needed for EIP-2678 compatibility
        if "by_alias" not in kwargs:
            kwargs["by_alias"] = True

        # EIP-2678: skip empty fields (at least by default)
        if "exclude_none" not in kwargs:
            kwargs["exclude_none"] = True

        return super().dict(*args, **kwargs)

    def json(self, *args, **kwargs) -> str:
        # NOTE: When serializing to IPFS, the canonical representation must be repeatable

        # EIP-2678: minified representation (at least by default)
        if "separators" not in kwargs:
            kwargs["separators"] = (",", ":")

        # EIP-2678: sort keys (at least by default)
        if "sort_keys" not in kwargs:
            kwargs["sort_keys"] = True

        # NOTE: We do this to accomodate the aliases needed for EIP-2678 compatibility
        if "by_alias" not in kwargs:
            kwargs["by_alias"] = True

        # EIP-2678: skip empty fields (at least by default)
        if "exclude_none" not in kwargs:
            kwargs["exclude_none"] = True

        return super().json(*args, **kwargs)

    @classmethod
    @no_type_check
    def _get_value(
        cls,
        v: Any,
        *args,
        **kwargs,
    ) -> Any:

        if isinstance(v, HexBytes):
            return v.hex()

        return super()._get_value(
            v,
            *args,
            **kwargs,
        )
