from typing import Optional

from eth_typing import (
    Hash32,
)
from hexbytes import HexBytes

from trie.typing import (
    Nibbles,
    NibblesInput,
    HexaryTrieNode,
)


class InvalidNibbles(Exception):
    pass


class InvalidNode(Exception):
    pass


class ValidationError(Exception):
    pass


class BadTrieProof(Exception):
    pass


class NodeOverrideError(Exception):
    pass


class InvalidKeyError(Exception):
    pass


class SyncRequestAlreadyProcessed(Exception):
    pass


class MissingTrieNode(Exception):
    """
    Raised when a node of the trie is not available in the database,
    in the current state root.

    This may happen when trying to read out the value of a key, or when simply
    traversing the trie.
    """
    def __init__(
            self,
            missing_node_hash: Hash32,
            root_hash: Hash32,
            requested_key: bytes,
            prefix: Nibbles = None,
            *args):

        if not isinstance(missing_node_hash, bytes):
            raise TypeError("Missing node hash must be bytes, was: %r" % missing_node_hash)
        elif not isinstance(root_hash, bytes):
            raise TypeError("Root hash must be bytes, was: %r" % root_hash)
        elif not isinstance(requested_key, bytes):
            raise TypeError("Requested key must be bytes, was: %r" % requested_key)

        if prefix is not None:
            prefix_nibbles: Optional[Nibbles] = Nibbles(prefix)
        else:
            prefix_nibbles = None

        super().__init__(
            HexBytes(missing_node_hash),
            HexBytes(root_hash),
            HexBytes(requested_key),
            prefix_nibbles,
            *args,
        )

    def __repr__(self) -> str:
        return (
            f"MissingTrieNode({self.missing_node_hash!r}, {self.root_hash!r}, "
            f"{self.requested_key!r}, prefix={self.prefix!r})"
        )

    def __str__(self) -> str:
        return (
            f"Trie database is missing hash {self.missing_node_hash!r} needed to look up node at"
            f" prefix {self.prefix}, when searching for key {self.requested_key!r} at root"
            f" hash {self.root_hash!r}"
        )

    @property
    def missing_node_hash(self) -> HexBytes:
        return self.args[0]

    @property
    def root_hash(self) -> HexBytes:
        return self.args[1]

    @property
    def requested_key(self) -> HexBytes:
        return self.args[2]

    @property
    def prefix(self) -> Optional[Nibbles]:
        """
        The tuple of nibbles that navigate to the missing node. For example, a missing
        root would have a prefix of (), and a missing left-most child of the
        root would have a prefix of (0, ).
        """
        return self.args[3]


class MissingTraversalNode(Exception):
    """
    Raised when a node of the trie is not available in the database,
    during HexaryTrie.traverse() or .traverse_from().

    This is triggered in the same situation as MissingTrieNode, but with less
    information available, because traversal can start from the middle of a trie.
        - traverse_from() ignore's the trie's root, so the root hash is unknown
        - the requested_key and prefix are unavailable because only the suffix of the key is known
    """
    def __init__(self, missing_node_hash: Hash32, nibbles_traversed: NibblesInput, *args) -> None:
        if not isinstance(missing_node_hash, bytes):
            raise TypeError("Missing node hash must be bytes, was: %r" % missing_node_hash)

        super().__init__(HexBytes(missing_node_hash), Nibbles(nibbles_traversed), *args)

    def __repr__(self) -> str:
        return f"MissingTraversalNode({self.missing_node_hash!r}, {self.nibbles_traversed!r})"

    def __str__(self) -> str:
        return (
            f"Trie database is missing hash {self.missing_node_hash!r}, found when traversing "
            f"down {self.nibbles_traversed}."
        )

    @property
    def missing_node_hash(self) -> HexBytes:
        return self.args[0]

    @property
    def nibbles_traversed(self) -> Nibbles:
        """
        Nibbles traversed down from the starting node to the missing node.
        """
        return self.args[1]


class TraversedPartialPath(Exception):
    """
    Raised when a traversal key ends in the middle of a partial path. It might be in
    an extension node or a leaf node.
    """
    def __init__(
            self,
            nibbles_traversed: NibblesInput,
            node: HexaryTrieNode,
            untraversed_tail: NibblesInput,
            *args) -> None:

        super().__init__(
            Nibbles(nibbles_traversed),
            node,
            Nibbles(untraversed_tail),
            *args,
        )
        self._simulated_node = self._make_simulated_node()

    def __repr__(self) -> str:
        return (
            f"TraversedPartialPath({self.nibbles_traversed}, {self.node},"
            f" {self.untraversed_tail})"
        )

    def __str__(self) -> str:
        return (
            f"Could not traverse through {self.node} at {self.nibbles_traversed}, only partially"
            f" traversed with: {self.untraversed_tail}"
        )

    @property
    def nibbles_traversed(self) -> Nibbles:
        """
        The nibbles traversed until the attached node, which could not be traversed into.
        """
        return self.args[0]

    @property
    def node(self) -> HexaryTrieNode:
        """
        The node which could not be traversed into. This is any leaf, or an extension node
        where traversal went part-way into the path. It must not be a branch node.
        """
        return self.args[1]

    @property
    def untraversed_tail(self) -> Nibbles:
        """
        The nibbles that only reached partially into the extension or leaf node.
        """
        return self.args[2]

    @property
    def simulated_node(self) -> HexaryTrieNode:
        """
        For the purposes of walking a trie, we might only be interested in the sub_segments,
        suffix, etc, of the node -- but assuming we actually had a node immediately at the
        requested prefix. This returns a node simulated as if that were true.

        See the trie walk tests for an example of how this is used.
        """
        return self._simulated_node

    def _make_simulated_node(self) -> HexaryTrieNode:
        from trie.utils.nodes import (
            key_starts_with,
            compute_extension_key,
            compute_leaf_key,
        )

        actual_node = self.node
        key_tail = self.untraversed_tail
        actual_sub_segments = actual_node.sub_segments

        if len(key_tail) == 0:
            raise ValueError(
                "Can only raise a TraversedPartialPath when some series of nibbles was untraversed"
            )

        if len(actual_sub_segments) == 0:
            if not key_starts_with(actual_node.suffix, key_tail):
                raise ValidationError(
                    f"Internal traverse bug: {actual_node.suffix} does not start with {key_tail}"
                )
            else:
                trimmed_suffix = Nibbles(actual_node.suffix[len(key_tail):])

            return HexaryTrieNode(
                (),
                actual_node.value,
                trimmed_suffix,
                [compute_leaf_key(trimmed_suffix), actual_node.raw[1]],
            )
        elif len(actual_sub_segments) == 1:
            extension = actual_sub_segments[0]
            if not key_starts_with(extension, key_tail):
                raise ValidationError(
                    f"Internal traverse bug: extension {extension} does not start with {key_tail}"
                )
            elif len(key_tail) == len(extension):
                raise ValidationError(
                    f"Internal traverse bug: {key_tail} should not equal {extension}"
                )
            else:
                trimmed_extension = Nibbles(extension[len(key_tail):])

            return HexaryTrieNode(
                (trimmed_extension,),
                actual_node.value,
                actual_node.suffix,
                [compute_extension_key(trimmed_extension), actual_node.raw[1]],
            )
        else:
            raise ValidationError(
                f"Can only partially traverse into leaf or extension, got {actual_node}"
            )


class PerfectVisibility(Exception):
    """
    Raised when calling :class:`trie.fog.HexaryTrieFog` methods that look for unknown prefixes,
    like :meth:`~trie.fog.HexaryTrieFog.nearest_unknown`, and there are no unknown parts of
    the trie. (in other words the fog reports :meth:`~trie.fog.HexaryTrieFog.is_complete` as True.
    """
    pass


class FullDirectionalVisibility(Exception):
    """
    Raised when calling :meth:`trie.fog.HexaryTrieFog.nearest_right`, and there are no unknown
    prefixes *in that direction* of the trie. (The fog may not report
    :meth:`~trie.fog.HexaryTrieFog.is_complete` as True, because more may be available to the left).
    """
    pass
