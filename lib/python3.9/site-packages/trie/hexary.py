from collections import defaultdict
import contextlib
import functools
import itertools
from typing import (
    Callable,
    Tuple,
    TypeVar,
    cast,
)

from rlp.codec import encode_raw

from eth_hash.auto import (
    keccak,
)

from eth_utils import (
    to_list,
    to_tuple,
)

from trie.constants import (
    BLANK_NODE,
    BLANK_NODE_HASH,
    NODE_TYPE_BLANK,
    NODE_TYPE_LEAF,
    NODE_TYPE_EXTENSION,
    NODE_TYPE_BRANCH,
)
from trie.exceptions import (
    BadTrieProof,
    MissingTraversalNode,
    MissingTrieNode,
    TraversedPartialPath,
    ValidationError,
)
from trie.typing import (
    Nibbles,
    NibblesInput,
    HexaryTrieNode,
    RawHexaryNode,
)
from trie.utils.db import (
    ScratchDB,
)
from trie.utils.nibbles import (
    bytes_to_nibbles,
    decode_nibbles,
    encode_nibbles,
)
from trie.utils.nodes import (
    annotate_node,
    decode_node,
    get_node_type,
    extract_key,
    compute_leaf_key,
    compute_extension_key,
    is_blank_node,
    is_extension_node,
    is_leaf_node,
    consume_common_prefix,
    key_starts_with,
)
from trie.validation import (
    validate_is_node,
    validate_is_bytes,
)

WrappedFunc = TypeVar('WrappedFunc', bound=Callable[..., None])


class _PartialTraversal(Exception):
    """
    Tried to navigate part-way into an extension node, when traversing a trie.

    An internal exception that should never escape the Trie.
    """
    pass


def prune_pending(fn: WrappedFunc) -> WrappedFunc:
    @functools.wraps(fn)
    def wrapped(trie_self, *args) -> None:
        with trie_self._prune_on_success():
            fn(trie_self, *args)
    return cast(WrappedFunc, wrapped)


class HexaryTrie:
    __slots__ = ('db', 'root_hash', 'is_pruning', '_ref_count', '_pending_prune_keys')

    # Shortcuts
    BLANK_NODE_HASH = BLANK_NODE_HASH
    BLANK_NODE = BLANK_NODE

    def __init__(self, db, root_hash=BLANK_NODE_HASH, prune=False, ref_count=None):
        """
        Important note about Pruning:

        The prune keyword is not intended for direct usage. It is likely
        to be changed or removed in future versions. If you want to prevent
        storage of unnecessary intermediate nodes, use the :meth:`squash_changes`
        context manager instead.

        Why? Unless working with an empty database, pruning will be overly aggressive,
        and delete nodes that are still used by other parts of the trie. This
        is prevented by squash_changes (by being overly conservative and not
        deleting any pre-existing nodes).
        """
        self.db = db
        validate_is_bytes(root_hash)
        self.root_hash = root_hash
        self.is_pruning = prune
        if ref_count is None:
            if prune:
                self._ref_count = defaultdict(int)
            else:
                self._ref_count = None
        else:
            if prune:
                self._ref_count = ref_count
            else:
                raise ValueError("Cannot pass an existing reference count in to a non-pruning trie")
        self._pending_prune_keys = None

    def get(self, key):
        validate_is_bytes(key)

        trie_key = bytes_to_nibbles(key)
        root_hash = self.root_hash
        try:
            return self._get(root_hash, trie_key)
        except MissingTraversalNode as traverse_exc:
            raise MissingTrieNode(
                traverse_exc.missing_node_hash,
                root_hash,
                key,
                traverse_exc.nibbles_traversed,
            ) from traverse_exc

    def _get(self, root_hash, trie_key):
        node, remaining_key = self._traverse(root_hash, trie_key)

        node_type = get_node_type(node)

        if node_type == NODE_TYPE_BLANK:
            return BLANK_NODE
        elif node_type == NODE_TYPE_LEAF:
            if remaining_key == extract_key(node):
                return node[1]
            else:
                # Any remaining key that isn't an exact match for the leaf node must
                #   be pointing to a value that doesn't exist.
                return BLANK_NODE
        elif node_type == NODE_TYPE_EXTENSION:
            if len(remaining_key) > 0:
                # Any remaining key should have traversed down into the extension's child.
                #   (or returned a blank node if the key didn't match the extension)
                raise ValidationError(
                    "Traverse should never return an extension node with remaining key, "
                    f"but returned node {node!r} with remaining key {remaining_key}."
                )
            else:
                return BLANK_NODE
        elif node_type == NODE_TYPE_BRANCH:
            if len(remaining_key) > 0:
                # Any remaining key should have traversed down into the branch's child, even
                #   if the branch had an empty child, which would then return a BLANK_NODE.
                raise ValidationError(
                    "Traverse should never return a non-empty branch node with remaining key, "
                    f"but returned node {node!r} with remaining key {remaining_key}."
                )
            else:
                return node[-1]
        else:
            raise Exception("Invariant: This shouldn't ever happen")

    def traverse(self, trie_key_input: NibblesInput) -> HexaryTrieNode:
        """
        Find the node at the path of nibbles provided. The most trivial example is
        to get the root node, using ``traverse(())``.

        :param trie_key_input: the series of nibbles to traverse to arrive at the node of interest
        :return: annotated node at the given path
        :raises MissingTraversalNode: if a node body is missing from the database
        :raises TraversedPartialPath: if trie key extends part-way down an extension or leaf node
        """
        trie_key = Nibbles(trie_key_input)

        node, remaining_key = self._traverse(self.root_hash, trie_key)

        annotated_node = annotate_node(node)

        if remaining_key:
            path_to_node = trie_key[:len(trie_key) - len(remaining_key)]
            raise TraversedPartialPath(path_to_node, annotated_node, remaining_key)
        else:
            return annotated_node

    def _traverse(self, root_hash, trie_key) -> Tuple[RawHexaryNode, Nibbles]:
        try:
            root_node = self.get_node(root_hash)
        except KeyError:
            raise MissingTraversalNode(root_hash, ())

        return self._traverse_from(root_node, trie_key)

    def traverse_from(self, parent_node: HexaryTrieNode, trie_key_input: Nibbles) -> HexaryTrieNode:
        """
        Find the node at the path of nibbles provided. You cannot navigate to the root node
        this way (without already having the root node body, to supply as the argument).

        The trie does *not* re-verify the path/hashes from the node prefix to the node.

        :param trie_key_input: the sub-key used to traverse from the given node to the returned node
        :raises MissingTraversalNode: if a node body is missing from the database
        :raises TraversedPartialPath: if trie key extends part-way down an extension or leaf node
        """
        trie_key = Nibbles(trie_key_input)

        node, remaining_key = self._traverse_from(parent_node.raw, trie_key)

        annotated_node = annotate_node(node)

        if remaining_key:
            path_to_node = trie_key[:len(trie_key) - len(remaining_key)]
            raise TraversedPartialPath(path_to_node, annotated_node, remaining_key)
        else:
            return annotated_node

    def _traverse_from(self, node: RawHexaryNode, trie_key) -> Tuple[RawHexaryNode, Nibbles]:
        """
        Traverse down the trie from the given node, using the trie_key to navigate.

        At each node, consume a prefix from the key, and navigate to its child. Repeat with that
        child node and so on, until:
        - there is no key remaining, or
        - the child node is a blank node, or
        - the child node is a leaf node

        :return: (the deepest child node, the unconsumed suffix of the key)
        :raises MissingTraversalNode: if a node body is missing from the database
        """
        remaining_key = trie_key
        while remaining_key:
            node_type = get_node_type(node)

            if node_type == NODE_TYPE_BLANK:
                return BLANK_NODE, ()  # type: ignore # mypy thinks BLANK_NODE != b''
            elif node_type == NODE_TYPE_LEAF:
                leaf_key = extract_key(node)
                if key_starts_with(leaf_key, remaining_key):
                    return node, remaining_key
                else:
                    # The trie key and leaf node key branch away from each other, so there
                    # is no node at the specified key.
                    return BLANK_NODE, ()  # type: ignore # mypy thinks BLANK_NODE != b''
            elif node_type == NODE_TYPE_EXTENSION:
                try:
                    next_node_pointer, remaining_key = self._traverse_extension(node, remaining_key)
                except _PartialTraversal:
                    # could only descend part-way into an extension node
                    return node, remaining_key
            elif node_type == NODE_TYPE_BRANCH:
                next_node_pointer = node[remaining_key[0]]
                remaining_key = remaining_key[1:]
            else:
                raise Exception("Invariant: This shouldn't ever happen")

            try:
                node = self.get_node(next_node_pointer)
            except KeyError as exc:
                used_key = trie_key[:len(trie_key) - len(remaining_key)]

                raise MissingTraversalNode(exc.args[0], used_key)

        # navigated down the full key
        return node, Nibbles(())

    def _traverse_extension(self, node, trie_key):
        current_key = extract_key(node)

        common_prefix, current_key_remainder, trie_key_remainder = consume_common_prefix(
            current_key,
            trie_key,
        )

        if len(current_key_remainder) == 0:
            # The full extension node's key was consumed
            return node[1], trie_key_remainder
        elif len(trie_key_remainder) == 0:
            # The trie key was consumed before reaching the end of the extension node's key
            raise _PartialTraversal
        else:
            # The trie key and extension node key branch away from each other, so there
            # is no node at the specified key.
            return BLANK_NODE, ()

    def _raise_missing_node(self, exception, key):
        # Indicate more information about which key was requested, which node was missing, etc
        raise MissingTrieNode(exception.args[0], self.root_hash, key, prefix=None) from exception

    @prune_pending
    def set(self, key, value):
        validate_is_bytes(key)
        validate_is_bytes(value)

        trie_key = bytes_to_nibbles(key)

        try:
            root_node = self.get_node(self.root_hash)

            if value == b'':
                new_node = self._delete(root_node, trie_key)
            else:
                new_node = self._set(root_node, trie_key, value)
        except KeyError as exc:
            self._raise_missing_node(exc, key)

        self._set_root_node(new_node)

    def _set(self, node, trie_key, value):
        node_type = get_node_type(node)

        self._prune_node(node)

        if node_type == NODE_TYPE_BLANK:
            return [
                compute_leaf_key(trie_key),
                value,
            ]
        elif node_type in {NODE_TYPE_LEAF, NODE_TYPE_EXTENSION}:
            return self._set_kv_node(node, trie_key, value)
        elif node_type == NODE_TYPE_BRANCH:
            return self._set_branch_node(node, trie_key, value)
        else:
            raise Exception("Invariant: This shouldn't ever happen")

    def exists(self, key):
        validate_is_bytes(key)

        return self.get(key) != BLANK_NODE

    @prune_pending
    def delete(self, key):
        validate_is_bytes(key)

        trie_key = bytes_to_nibbles(key)

        try:
            root_node = self.get_node(self.root_hash)

            new_node = self._delete(root_node, trie_key)
        except KeyError as exc:
            self._raise_missing_node(exc, key)

        self._set_root_node(new_node)

    def _delete(self, node, trie_key):
        node_type = get_node_type(node)

        self._prune_node(node)

        if node_type == NODE_TYPE_BLANK:
            # ignore attempt to delete key from empty node
            return BLANK_NODE
        elif node_type in {NODE_TYPE_LEAF, NODE_TYPE_EXTENSION}:
            return self._delete_kv_node(node, trie_key)
        elif node_type == NODE_TYPE_BRANCH:
            return self._delete_branch_node(node, trie_key)
        else:
            raise Exception("Invariant: This shouldn't ever happen")

    @property
    def ref_count(self):
        if self._ref_count is None:
            raise Exception("Trie does not track node usage unless pruning is enabled")
        else:
            return self._ref_count

    #
    # Trie Proofs
    #
    @classmethod
    def get_from_proof(cls, root_hash, key, proof):
        trie = cls({})

        for node in proof:
            trie._set_raw_node(node)

        with trie.at_root(root_hash) as proven_snapshot:
            try:
                return proven_snapshot.get(key)
            except MissingTrieNode as e:
                raise BadTrieProof("Missing proof node with hash {}".format(e.missing_node_hash))

    def get_proof(self, key):
        validate_is_bytes(key)

        node = self.get_node(self.root_hash)
        trie_key = bytes_to_nibbles(key)

        return self._get_proof(node, trie_key)

    def _get_proof(self, node, trie_key, proven_len=0, last_proof=tuple()):
        updated_proof = last_proof + (node, )
        unproven_key = trie_key[proven_len:]

        node_type = get_node_type(node)
        if node_type == NODE_TYPE_BLANK:
            return last_proof
        elif node_type == NODE_TYPE_LEAF:
            return updated_proof
        elif node_type == NODE_TYPE_EXTENSION:
            current_key = extract_key(node)
            if key_starts_with(unproven_key, current_key):
                next_node = self.get_node(node[1])
                new_proven_len = proven_len + len(current_key)
                return self._get_proof(next_node, trie_key, new_proven_len, updated_proof)
            else:
                return updated_proof
        elif node_type == NODE_TYPE_BRANCH:
            if not unproven_key:
                return updated_proof
            next_node = self.get_node(node[unproven_key[0]])
            new_proven_len = proven_len + 1
            return self._get_proof(next_node, trie_key, new_proven_len, updated_proof)
        else:
            raise Exception("Invariant: This shouldn't ever happen")

    #
    # Convenience
    #
    @property
    def root_node(self) -> HexaryTrieNode:
        try:
            raw_node = self.get_node(self.root_hash)
        except KeyError:
            raise MissingTraversalNode(self.root_hash, nibbles_traversed=())
        else:
            return annotate_node(raw_node)

    #
    # Utils
    #

    @contextlib.contextmanager
    def _prune_on_success(self):
        if self.is_pruning:
            if self._pending_prune_keys is None:
                self._pending_prune_keys = defaultdict(int)
            else:
                raise ValidationError("Cannot set/delete simultaneously, run them in serial")
        try:
            yield
            if self.is_pruning:
                self._complete_pruning()
        finally:
            # Reset for next set/delete
            self._pending_prune_keys = None

    def _prune_node(self, node):
        """
        Prune the given node if context exits cleanly.
        """
        if self.is_pruning:
            prune_key, node_body = self._node_to_db_mapping(node)
            if node_body is not None:
                self._pending_prune_keys[prune_key] += 1

    def _complete_pruning(self):
        for key, number_prunes in self._pending_prune_keys.items():
            new_count = self._ref_count[key] - number_prunes

            if new_count <= 0:
                # Ref count doesn't track keys that are already in the starting database,
                #   so ref count can go negative. Then, detect if key is in underlying:
                #   - If so, delete it and set the refcount down to 0
                #   - If not, raise an exception about trying to prune a node that doesn't exist
                try:
                    del self.db[key]
                except KeyError as exc:
                    raise ValidationError("Tried to prune key %r that doesn't exist" % key) from exc
                else:
                    new_count = 0

            if new_count == 0:
                # This is an optimization, to reduce the size of the _ref_count dict
                del self._ref_count[key]
            else:
                self._ref_count[key] = new_count

    def regenerate_ref_count(self):
        new_ref_count = defaultdict(int)

        keys_to_count = [self.root_hash]
        while keys_to_count:
            key = keys_to_count.pop()
            if key == b'' or isinstance(key, list) or key == BLANK_NODE_HASH:
                continue
            new_ref_count[key] += 1

            node = self.get_node(key)
            node_type = get_node_type(node)

            if node_type == NODE_TYPE_BLANK:
                continue
            if node_type == NODE_TYPE_BRANCH:
                keys_to_count.extend(node[:16])
            elif node_type == NODE_TYPE_EXTENSION:
                keys_to_count.append(node[1])

        return new_ref_count

    def _set_raw_node(self, raw_node):
        key, value = self._node_to_db_mapping(raw_node)
        if key == BLANK_NODE:
            # skip saving the blank node to DB
            return BLANK_NODE_HASH

        if value is None:
            # Some nodes are so small that they are not encoded during _node_to_db_mapping,
            # so we manually encode and hash it here:
            encoded_node = encode_raw(key)
            node_hash = keccak(encoded_node)
        else:
            encoded_node = value
            node_hash = key

        self._set_db_value(node_hash, encoded_node)
        return node_hash

    def _set_db_value(self, key, value):
        self.db[key] = value
        if self.is_pruning:
            self._ref_count[key] += 1

    def _set_root_node(self, root_node):
        validate_is_node(root_node)

        if self.is_pruning:
            # Root nodes are special: they are always hashed, which is a surprise to the rest of
            #   the pruning logic. We have to catch if the root node is small and prune it here.
            old_root_hash = self.root_hash
            if old_root_hash != BLANK_NODE_HASH:
                try:
                    old_root_node = self.get_node(old_root_hash)
                except KeyError:
                    # The old root node is missing from the database, but the only
                    #   reason we were retrieving it is to potentially prune it away.
                    # So just ignore the pruning if the old node is already missing
                    pass
                else:
                    prune_key, node_body = self._node_to_db_mapping(old_root_node)
                    if node_body is None and old_root_hash in self.db:
                        self._pending_prune_keys[old_root_hash] += 1

        self.root_hash = self._set_raw_node(root_node)

    def get_node(self, node_hash):
        if node_hash == BLANK_NODE:
            return BLANK_NODE
        elif node_hash == BLANK_NODE_HASH:
            return BLANK_NODE

        if len(node_hash) < 32:
            encoded_node = node_hash
        else:
            encoded_node = self.db[node_hash]
        node = decode_node(encoded_node)

        return node

    def _node_to_db_mapping(self, node):
        if self.is_pruning and isinstance(node, list):
            # When self.is_pruning is True, we'll often prune nodes that have been inserted
            # recently, so this hack allows us to use an LRU-cached implementation of
            # _node_to_db_mapping(), which improves the performance of _prune_node()
            # significantly.
            return self._cached_create_node_to_db_mapping(tuplify(node))
        else:
            return self._create_node_to_db_mapping(node)

    @functools.lru_cache(4096)
    def _cached_create_node_to_db_mapping(self, node):
        if isinstance(node, tuple):
            node = listify(node)
        return self._create_node_to_db_mapping(node)

    def _create_node_to_db_mapping(self, node):
        validate_is_node(node)
        if is_blank_node(node):
            return BLANK_NODE, None
        encoded_node = encode_raw(node)
        if len(encoded_node) < 32:
            return node, None

        encoded_node_hash = keccak(encoded_node)
        return encoded_node_hash, encoded_node

    def _persist_node(self, node):
        key, value = self._node_to_db_mapping(node)
        if value is not None:
            self._set_db_value(key, value)
        return key

    #
    # Node Operation Helpers
    def _normalize_branch_node(self, node):
        """
        A branch node which is left with only a single non-blank item should be
        turned into either a leaf or extension node.
        """
        iter_node = iter(node)
        if any(iter_node) and any(iter_node):
            return node

        if node[-1]:
            return [compute_leaf_key([]), node[-1]]

        sub_node_idx, sub_node_hash = next(
            (idx, v)
            for idx, v
            in enumerate(node[:16])
            if v
        )
        sub_node = self.get_node(sub_node_hash)
        sub_node_type = get_node_type(sub_node)

        if sub_node_type in {NODE_TYPE_LEAF, NODE_TYPE_EXTENSION}:
            self._prune_node(sub_node)

            new_subnode_key = encode_nibbles(tuple(itertools.chain(
                [sub_node_idx],
                decode_nibbles(sub_node[0]),
            )))
            return [new_subnode_key, sub_node[1]]
        elif sub_node_type == NODE_TYPE_BRANCH:
            return [encode_nibbles([sub_node_idx]), sub_node_hash]
        else:
            raise Exception("Invariant: this code block should be unreachable")

    #
    # Node Operations
    #
    def _delete_branch_node(self, node, trie_key):
        """
        Delete a key from inside or underneath a branch node
        """
        if not trie_key:
            node[-1] = BLANK_NODE
            return self._normalize_branch_node(node)

        node_to_delete = self.get_node(node[trie_key[0]])

        sub_node = self._delete(node_to_delete, trie_key[1:])
        encoded_sub_node = self._persist_node(sub_node)

        if encoded_sub_node == node[trie_key[0]]:
            # If no change, (value already empty), short-circuit and skip any other work.
            return node

        node[trie_key[0]] = encoded_sub_node
        if encoded_sub_node == BLANK_NODE:
            return self._normalize_branch_node(node)

        return node

    def _delete_kv_node(self, node, trie_key):
        current_key = extract_key(node)

        if not key_starts_with(trie_key, current_key):
            # key not present?....
            return node

        node_type = get_node_type(node)

        if node_type == NODE_TYPE_LEAF:
            if trie_key == current_key:
                return BLANK_NODE
            else:
                return node

        sub_node_key = trie_key[len(current_key):]
        sub_node = self.get_node(node[1])

        new_sub_node = self._delete(sub_node, sub_node_key)
        encoded_new_sub_node = self._persist_node(new_sub_node)

        if encoded_new_sub_node == node[1]:
            return node

        if new_sub_node == BLANK_NODE:
            return BLANK_NODE

        new_sub_node_type = get_node_type(new_sub_node)
        if new_sub_node_type in {NODE_TYPE_LEAF, NODE_TYPE_EXTENSION}:
            self._prune_node(new_sub_node)

            new_key = current_key + decode_nibbles(new_sub_node[0])
            return [encode_nibbles(new_key), new_sub_node[1]]

        if new_sub_node_type == NODE_TYPE_BRANCH:
            return [encode_nibbles(current_key), encoded_new_sub_node]

        raise Exception("Invariant, this code path should not be reachable")

    def _set_branch_node(self, node, trie_key, value):
        if trie_key:
            sub_node = self.get_node(node[trie_key[0]])

            new_node = self._set(sub_node, trie_key[1:], value)
            node[trie_key[0]] = self._persist_node(new_node)
        else:
            node[-1] = value
        return node

    def _set_kv_node(self, node, trie_key, value):
        current_key = extract_key(node)
        common_prefix, current_key_remainder, trie_key_remainder = consume_common_prefix(
            current_key,
            trie_key,
        )
        is_extension = is_extension_node(node)

        if not current_key_remainder and not trie_key_remainder:
            if is_leaf_node(node):
                return [node[0], value]
            else:
                sub_node = self.get_node(node[1])
                new_node = self._set(sub_node, trie_key_remainder, value)
        elif not current_key_remainder:
            if is_extension:
                sub_node = self.get_node(node[1])
                new_node = self._set(sub_node, trie_key_remainder, value)
            else:
                subnode_position = trie_key_remainder[0]
                subnode_key = compute_leaf_key(trie_key_remainder[1:])
                sub_node = [subnode_key, value]

                new_node = [BLANK_NODE] * 16 + [node[1]]
                new_node[subnode_position] = self._persist_node(sub_node)
        else:
            new_node = [BLANK_NODE] * 17

            if len(current_key_remainder) == 1 and is_extension:
                new_node[current_key_remainder[0]] = node[1]
            else:
                if is_extension:
                    compute_key_fn = compute_extension_key
                else:
                    compute_key_fn = compute_leaf_key

                new_node[current_key_remainder[0]] = self._persist_node([
                    compute_key_fn(current_key_remainder[1:]),
                    node[1],
                ])

            if trie_key_remainder:
                new_node[trie_key_remainder[0]] = self._persist_node([
                    compute_leaf_key(trie_key_remainder[1:]),
                    value,
                ])
            else:
                new_node[-1] = value

        if common_prefix:
            new_node_key = self._persist_node(new_node)
            return [compute_extension_key(common_prefix), new_node_key]
        else:
            return new_node

    #
    # Dictionary API
    #
    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __delitem__(self, key):
        return self.delete(key)

    def __contains__(self, key):
        return self.exists(key)

    #
    # Context APIs
    #
    @contextlib.contextmanager
    def squash_changes(self):
        scratch_db = ScratchDB(self.db)
        with scratch_db.batch_commit(do_deletes=self.is_pruning):
            Trie = type(self)
            memory_trie = Trie(scratch_db, self.root_hash, prune=True, ref_count=self._ref_count)
            yield memory_trie

        if self.root_hash != memory_trie.root_hash:
            try:
                raw_root_node = memory_trie.get_node(memory_trie.root_hash)
            except KeyError:
                # if the new root node is missing, then we shouldn't crash here
                self.root_hash = memory_trie.root_hash
            else:
                self.root_hash = self._set_raw_node(raw_root_node)

    @contextlib.contextmanager
    def at_root(self, at_root_hash):
        if self.is_pruning:
            raise ValidationError("Cannot use trie snapshot while pruning")

        snapshot = type(self)(self.db, at_root_hash, prune=False)
        yield snapshot

    def __repr__(self) -> str:
        return f"HexaryTrie({self.db!r}, root_hash={self.root_hash}, prune={self.is_pruning})"


@to_tuple
def tuplify(node):
    for sub in node:
        if isinstance(sub, list):
            yield tuplify(sub)
        else:
            yield sub


@to_list
def listify(node):
    for sub in node:
        if isinstance(sub, tuple):
            yield listify(sub)
        else:
            yield sub
