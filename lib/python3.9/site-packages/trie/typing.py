import enum
from typing import (
    Iterable,
    List,
    NamedTuple,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)
from typing_extensions import (
    Literal,
    Protocol,
)

from eth_utils import (
    is_list_like,
)


# The RLP-decoded node is either blank, or a list, full of bytes or recursive nodes
# Recursive definitions don't seem supported at the moment, follow:
#   https://github.com/python/mypy/issues/731
# Another option is to manually declare a few levels of the type. It should be possible
#   to determine the maximum number of embeds with single-nibble keys and single byte values.
RawHexaryNode = Union[
    # Blank node
    Literal[b''],

    # Leaf or extension node are length 2
    # Branch node is length 17
    List[Union[
        # keys, hashes to next nodes, and values
        bytes,

        # embedded subnodes
        "RawHexaryNode",
    ]],
]


class Nibble(enum.IntEnum):
    Hex0 = 0
    Hex1 = 1
    Hex2 = 2
    Hex3 = 3
    Hex4 = 4
    Hex5 = 5
    Hex6 = 6
    Hex7 = 7
    Hex8 = 8
    Hex9 = 9
    HexA = 0xA
    HexB = 0xB
    HexC = 0xC
    HexD = 0xD
    HexE = 0xE
    HexF = 0xF

    def __repr__(self):
        return hex(self.value)


# A user-input value, where each element will be validated as a Nibble instead of int
NibblesInput = Sequence[int]


class Nibbles(Tuple[Nibble, ...]):
    def __new__(cls, nibbles: NibblesInput) -> 'Nibbles':
        if type(nibbles) is Nibbles:
            # instanceof thinks that a Tuple[Nibble, ...] *is* a Nibbles, so we use
            #   a stricter type check here
            return nibbles  # type: ignore  # mypy doesn't recognize that this is now a Nibbles
        elif not is_list_like(nibbles):
            raise TypeError(f"Must pass in a tuple of nibbles, but got {nibbles!r}")
        else:
            return tuple.__new__(cls, (Nibble(maybe_nibble) for maybe_nibble in nibbles))

    def __add__(self, other: Tuple[Nibble, ...]) -> 'Nibbles':
        return Nibbles(super().__add__(other))

    def _repr_pretty_(self, p, cycle: bool) -> None:
        # Weird, ipython seems to drop the trailing comma in the pretty repr they do. Fixing...
        if cycle:
            p.text('(...)')
        else:
            p.text(super().__repr__())


class HexaryTrieNode(NamedTuple):
    """
    Public API for a node of a trie, it is pre-processed a bit for simplicity.
    """

    sub_segments: Tuple[Nibbles, ...]
    """
    Sub segments are the _complete_ list of possible subkeys.
    All sub segments *not* listed can be considered to not exist.
    Sub segments are sorted.

    Each sub segment does not include the trie node prefix. For example:
        - Branch nodes have length-1 tuples as sub_segments.
        - Leaf nodes have no sub_segments
        - Extension nodes have one sub_segment
    """

    value: bytes
    """
    This is the value associated with the key which navigates to this node in
    the trie. If empty, will be set to b''.
    """

    suffix: Nibbles
    """
    In a leaf node, there is a suffix of a key remaining before the value is reached.
    This is that series of nibbles. On a branch node with a value, the suffix will be ().
    """

    raw: RawHexaryNode
    """
    The node body, which is useful for calls to HexaryTrie.traverse_from(...),
    for faster access of sub-nodes.
    """


T = TypeVar('T')


class GenericSortedSet(Protocol[T]):
    """
    A protocol definining the minimal subset of features used from
    sortedcontainers.SortedSet. Feel free to add more as needed.
    """
    def __contains__(self, search_value: T) -> bool:
        ...

    def __getitem__(self, index: int) -> T:
        ...

    def __len__(self) -> int:
        ...

    def __iter__(self) -> 'GenericSortedSet[T]':
        ...

    def __next__(self) -> T:
        ...

    def bisect(self, search_value: T) -> int:
        ...

    def copy(self) -> 'GenericSortedSet[T]':
        ...

    def remove(self, to_remove: T) -> None:
        ...

    def update(self, new_values: Iterable[T]) -> None:
        ...
