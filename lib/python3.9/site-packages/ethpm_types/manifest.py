from typing import Dict, List, Optional

from pydantic import AnyUrl, Field, root_validator, validator

from .base import BaseModel
from .contract_type import BIP122_URI, ContractInstance, ContractType
from .source import Compiler, Source

ALPHABET = set("abcdefghijklmnopqrstuvwxyz")
NUMBERS = set("0123456789")


class PackageName(str):
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            pattern="^[a-z][-a-z0-9]{0,254}$",
            examples=["my-token", "safe-math", "nft"],
        )

    @classmethod
    def __get_validators__(cls):
        yield cls.check_length
        yield cls.check_first_character
        yield cls.check_valid_characters

    @classmethod
    def check_length(cls, value):
        assert 0 < len(value) < 256, "Length must be between 1 and 255"
        return value

    @classmethod
    def check_first_character(cls, value):
        assert value[0] in ALPHABET, "First character in name must be a-z"
        return value

    @classmethod
    def check_valid_characters(cls, value):
        assert set(value) < ALPHABET.union(NUMBERS).union(
            "-"
        ), "Characters in name must be one of a-z or 0-9 or '-'"
        return value

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"


class PackageMeta(BaseModel):
    authors: Optional[List[str]] = None
    license: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    links: Optional[Dict[str, AnyUrl]] = None


class PackageManifest(BaseModel):
    manifest: str = "ethpm/3"
    name: Optional[PackageName] = None
    # NOTE: ``version`` should be valid SemVer
    version: Optional[str] = None
    # NOTE: ``meta`` should be in all published packages
    meta: Optional[PackageMeta] = None
    # NOTE: ``sources`` source tree should be necessary and sufficient to compile
    #       all ``ContractType``s in manifest
    sources: Optional[Dict[str, Source]] = None
    # NOTE: ``contractTypes`` should only include types directly computed from manifest
    # NOTE: ``contractTypes`` should not include types from dependencies
    # NOTE: ``contractTypes`` should not include abstracts
    contract_types: Optional[Dict[str, ContractType]] = Field(None, alias="contractTypes")
    compilers: Optional[List[Compiler]] = None
    # NOTE: ``str`` arg should be a valid ``contractType``, but this is not required.
    deployments: Optional[Dict[BIP122_URI, Dict[str, ContractInstance]]] = None
    # NOTE: values must be a Content Addressible URI that conforms to the same manifest
    #       version as ``manifest``
    dependencies: Optional[Dict[PackageName, AnyUrl]] = Field(None, alias="buildDependencies")

    @root_validator
    def check_valid_manifest_version(cls, values):
        # NOTE: We only support v3 (EIP-2678) of the ethPM spec currently
        if values["manifest"] != "ethpm/3":
            raise ValueError("only ethPM v3 (EIP-2678) supported")

        return values

    @root_validator
    def check_both_version_and_name(cls, values):
        if ("name" in values or "version" in values) and (
            "name" not in values or "version" not in values
        ):
            raise ValueError("Both `name` and `version` must be present if either is specified")

        return values

    @root_validator
    def check_contract_source_ids(cls, values):
        if (
            "contract_types" in values
            and values["contract_types"] is not None
            and "sources" in values
            and values["sources"] is not None
        ):
            for alias in values["contract_types"]:
                source_id = values["contract_types"][alias].source_id
                if source_id and (source_id not in values["sources"]):
                    raise ValueError(f"'{source_id}' missing from `sources`")

        return values

    @validator("contract_types")
    def add_name_to_contract_types(cls, values):
        aliases = list(values.keys())
        # NOTE: Must manually inject names to types here
        for alias in aliases:
            if not values[alias]:
                values[alias].name = alias
            # else: contractName != contractAlias (key used in `contractTypes` dict)

        return values

    def __getattr__(self, attr_name: str):
        # NOTE: **must** raise `AttributeError` or return here, or else Python breaks
        if self.contract_types and attr_name in self.contract_types:
            return self.contract_types[attr_name]

        else:
            raise AttributeError(f"{self.__class__.__name__} has no contract type '{attr_name}'")
