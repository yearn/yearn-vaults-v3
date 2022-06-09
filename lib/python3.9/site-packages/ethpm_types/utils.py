from enum import Enum
from hashlib import md5, sha3_256, sha256

from hexbytes import HexBytes as BaseHexBytes

CONTENT_ADDRESSED_SCHEMES = {"ipfs"}


class HexBytes(BaseHexBytes):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        return HexBytes(v)


class Algorithm(str, Enum):
    MD5 = "md5"
    SHA3 = "sha3"
    SHA256 = "sha256"


def is_valid_hex(data: str) -> bool:
    if not data.startswith("0x"):
        return False

    if set(data[2:].lower()) > set("1234567890abcdef"):
        return False

    if len(data) % 2 != 0:
        return False

    return True


class Hex(str):
    """A hex string value, typically from a hash."""

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            pattern="^0x([0-9a-f][0-9a-f])*$",
            examples=[
                "0x",  # empty bytes
                "0xd4",
                "0xd4e5",
                "0xd4e56740",
                "0xd4e56740f876aef8",
                "0xd4e56740f876aef8c010b86a40d5f567",
                "0xd4e56740f876aef8c010b86a40d5f56745a118d0906a34e69aec8c0db1cb8fa3",
            ],
        )

    @classmethod
    def __get_validators__(cls):
        yield cls.validate_hex

    @classmethod
    def validate_hex(cls, data: str) -> str:
        if not is_valid_hex(data):
            raise ValueError("Invalid Hex Value")

        return data

    @classmethod
    def from_bytes(cls, data: bytes) -> "Hex":
        return cls("0x" + data.hex())

    def to_bytes(self) -> bytes:
        return bytes.fromhex(self[2:])


def compute_checksum(content: bytes, algorithm: Algorithm = Algorithm.MD5) -> Hex:
    if algorithm is Algorithm.MD5:
        return Hex.from_bytes(md5(content).digest())

    elif algorithm is Algorithm.SHA3:
        return Hex.from_bytes(sha3_256(content).digest())

    elif algorithm is Algorithm.SHA256:
        return Hex.from_bytes(sha256(content).digest())

    # TODO: Support IPFS CIDv0 & CIDv1
    # TODO: Support keccak256 (if even necessary, mentioned in EIP but not used)
    # TODO: Explore other algorithms needed
    else:
        raise ValueError("Unsupported algorithm")
