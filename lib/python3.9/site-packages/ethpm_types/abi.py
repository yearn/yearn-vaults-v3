from typing import List, Optional, Union

from pydantic import Extra

from .base import BaseModel

try:
    from typing import Literal  # type: ignore
except ImportError:
    from typing_extensions import Literal  # type: ignore


class ABIType(BaseModel):
    name: Optional[str] = None  # NOTE: Tuples don't have names by default
    type: Union[str, "ABIType"]
    components: Optional[List["ABIType"]] = None  # NOTE: Tuples/Structs have this field
    internalType: Optional[str] = None  # Some compilers insert this field, can have useful info

    class Config:
        extra = Extra.allow
        allow_mutation = False

    @property
    def canonical_type(self) -> str:
        if "tuple" in self.type and self.components:  # NOTE: 2nd condition just to satisfy mypy
            value = f"({','.join(m.canonical_type for m in self.components)})"
            if "[" in self.type:
                value += f"[{str(self.type).split('[')[-1]}"

            return value

        elif isinstance(self.type, str):
            return self.type

        else:
            # Recursively discover the canonical type
            return self.type.canonical_type

    @property
    def signature(self) -> str:
        if self.name:
            return f"{self.canonical_type} {self.name}"
        else:
            return self.canonical_type


class EventABIType(ABIType):
    indexed: bool = False  # Only event ABI types should have this field

    @property
    def signature(self) -> str:
        sig = self.canonical_type
        # For events (handles both None and False conditions)
        if self.indexed:
            sig += " indexed"
        if self.name:
            sig += f" {self.name}"
        return sig


class ConstructorABI(BaseModel):
    type: Literal["constructor"]

    # No `name` field
    stateMutability: str = "nonpayable"  # NOTE: Should be either "payable" or "nonpayable"

    inputs: List[ABIType] = []

    @property
    def is_payable(self) -> bool:
        return self.stateMutability == "payable"

    @property
    def signature(self) -> str:
        """
        String representing the function signature, which includes the arg names and types,
        for display purposes only
        """
        input_args = ", ".join(i.signature for i in self.inputs)
        return f"constructor({input_args})"


class FallbackABI(BaseModel):
    type: Literal["fallback"]

    # No `name` field
    stateMutability: str = "nonpayable"  # NOTE: Should be either "payable" or "nonpayable"

    @property
    def is_payable(self) -> bool:
        return self.stateMutability == "payable"

    @property
    def signature(self) -> str:
        """
        String representing the function signature for display purposes only.
        """
        return "fallback()"


class ReceiveABI(BaseModel):
    type: Literal["receive"]

    # No `name` field
    stateMutability: Literal["payable"]

    @property
    def is_payable(self) -> bool:
        return True

    @property
    def signature(self) -> str:
        """
        String representing the function signature for display purposes only.
        """
        return "receive()"


class MethodABI(BaseModel):
    type: Literal["function"]

    name: str
    stateMutability: str = "nonpayable"

    inputs: List[ABIType] = []
    outputs: List[ABIType] = []

    @property
    def is_payable(self) -> bool:
        return self.stateMutability == "payable"

    @property
    def is_stateful(self) -> bool:
        return self.stateMutability not in ("view", "pure")

    @property
    def selector(self) -> str:
        """
        String representing the function selector, used to compute ``method_id``.
        """
        # NOTE: There is no space between input args for selector
        input_names = ",".join(i.canonical_type for i in self.inputs)
        return f"{self.name}({input_names})"

    @property
    def signature(self) -> str:
        """
        String representing the function signature, which includes the arg names and types,
        and output names and type(s) (if any) for display purposes only.
        """
        input_args = ", ".join(i.signature for i in self.inputs)
        output_args = ""

        if self.outputs:
            output_args = " -> "
            if len(self.outputs) > 1:
                output_args += "(" + ", ".join(o.canonical_type for o in self.outputs) + ")"

            else:
                output_args += self.outputs[0].canonical_type

        return f"{self.name}({input_args}){output_args}"


class EventABI(BaseModel):
    type: Literal["event"]

    name: str
    inputs: List[EventABIType] = []
    anonymous: bool = False

    @property
    def selector(self) -> str:
        """
        String representing the event selector, used to compute ``event_id``.
        """
        # NOTE: There is no space between input args for selector
        input_names = ",".join(i.canonical_type for i in self.inputs)
        return f"{self.name}({input_names})"

    @property
    def signature(self) -> str:
        """
        String representing the event signature, which includes the arg names and types,
        and output names and type(s) (if any) for display purposes only.
        """
        input_args = ", ".join(i.signature for i in self.inputs)
        return f"{self.name}({input_args})"


class ErrorABI(BaseModel):
    type: Literal["error"]

    name: str
    inputs: List[ABIType] = []

    @property
    def selector(self) -> str:
        """
        String representing the event selector, used to compute ``event_id``.
        """
        # NOTE: There is no space between input args for selector
        input_names = ",".join(i.canonical_type for i in self.inputs)
        return f"{self.name}({input_names})"

    @property
    def signature(self) -> str:
        """
        String representing the event signature, which includes the arg names and types,
        and output names and type(s) (if any) for display purposes only.
        """
        input_args = ", ".join(i.signature for i in self.inputs)
        return f"{self.name}({input_args})"


class StructABI(BaseModel):
    type: Literal["struct"]

    name: str
    members: List[ABIType]

    class Config:
        extra = Extra.allow

    @property
    def selector(self) -> str:
        """
        String representing the struct selector.
        """
        # NOTE: There is no space between input args for selector
        input_names = ",".join(i.canonical_type for i in self.members)
        return f"{self.name}({input_names})"

    @property
    def signature(self) -> str:
        """
        String representing the struct signature, which includes the member names and types,
        and offsets (if any) for display purposes only.
        """
        members_str = ", ".join(m.signature for m in self.members)
        return f"{self.name}({members_str})"


class UnprocessedABI(BaseModel):
    type: str

    class Config:
        extra = Extra.allow

    @property
    def signature(self) -> str:
        return self.json()


ABI = Union[
    ConstructorABI,
    FallbackABI,
    ReceiveABI,
    MethodABI,
    EventABI,
    ErrorABI,
    StructABI,
    UnprocessedABI,
]
