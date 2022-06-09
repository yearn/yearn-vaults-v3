from eth_hash.auto import (
    keccak,
)

from trie.constants import (
    BLANK_HASH,
    KV_TYPE,
    BRANCH_TYPE,
    LEAF_TYPE,
    BYTE_0,
    BYTE_1,
)
from trie.exceptions import (
    NodeOverrideError,
)
from trie.utils.binaries import (
    encode_to_bin,
)
from trie.utils.nodes import (
    parse_node,
    encode_kv_node,
    encode_branch_node,
    encode_leaf_node,
    get_common_prefix_length,
)
from trie.validation import (
    validate_is_bytes,
    validate_is_bin_node,
)


class BinaryTrie(object):
    def __init__(self, db, root_hash=BLANK_HASH):
        self.db = db
        validate_is_bytes(root_hash)
        self.root_hash = root_hash

    def get(self, key):
        """
        Fetches the value with a given keypath from the given node.

        Key will be encoded into binary array format first.
        """
        validate_is_bytes(key)

        return self._get(self.root_hash, encode_to_bin(key))

    def _get(self, node_hash, keypath):
        """
        Note: keypath should be in binary array format, i.e., encoded by encode_to_bin()
        """
        # Empty trie
        if node_hash == BLANK_HASH:
            return None
        nodetype, left_child, right_child = parse_node(self.db[node_hash])
        # Key-value node descend
        if nodetype == LEAF_TYPE:
            if keypath:
                return None
            return right_child
        elif nodetype == KV_TYPE:
            # Keypath too short
            if not keypath:
                return None
            if keypath[:len(left_child)] == left_child:
                return self._get(right_child, keypath[len(left_child):])
            else:
                return None
        # Branch node descend
        elif nodetype == BRANCH_TYPE:
            # Keypath too short
            if not keypath:
                return None
            if keypath[:1] == BYTE_0:
                return self._get(left_child, keypath[1:])
            else:
                return self._get(right_child, keypath[1:])

    def set(self, key, value):
        """
        Sets the value at the given keypath from the given node

        Key will be encoded into binary array format first.
        """
        validate_is_bytes(key)
        validate_is_bytes(value)

        self.root_hash = self._set(self.root_hash, encode_to_bin(key), value)

    def _set(self, node_hash, keypath, value, if_delete_subtrie=False):
        """
        If if_delete_subtrie is set to True, what it will do is that it take in a keypath
        and traverse til the end of keypath, then delete the whole subtrie of that node.

        Note: keypath should be in binary array format, i.e., encoded by encode_to_bin()
        """
        # Empty trie
        if node_hash == BLANK_HASH:
            if value:
                return self._hash_and_save(
                    encode_kv_node(keypath, self._hash_and_save(encode_leaf_node(value)))
                )
            else:
                return BLANK_HASH
        nodetype, left_child, right_child = parse_node(self.db[node_hash])
        # Node is a leaf node
        if nodetype == LEAF_TYPE:
            # Keypath must match, there should be no remaining keypath
            if keypath:
                raise NodeOverrideError(
                    "Fail to set the value because the prefix of it's key"
                    " is the same as existing key")
            if if_delete_subtrie:
                return BLANK_HASH
            return self._hash_and_save(encode_leaf_node(value)) if value else BLANK_HASH
        # node is a key-value node
        elif nodetype == KV_TYPE:
            # Keypath too short
            if not keypath:
                if if_delete_subtrie:
                    return BLANK_HASH
                else:
                    raise NodeOverrideError(
                        "Fail to set the value because it's key"
                        " is the prefix of other existing key")
            return self._set_kv_node(
                keypath,
                node_hash,
                nodetype,
                left_child,
                right_child,
                value,
                if_delete_subtrie
            )
        # node is a branch node
        elif nodetype == BRANCH_TYPE:
            # Keypath too short
            if not keypath:
                if if_delete_subtrie:
                    return BLANK_HASH
                else:
                    raise NodeOverrideError(
                        "Fail to set the value because it's key"
                        " is the prefix of other existing key")
            return self._set_branch_node(
                keypath,
                nodetype,
                left_child,
                right_child,
                value,
                if_delete_subtrie
            )
        raise Exception("Invariant: This shouldn't ever happen")

    def _set_kv_node(
            self,
            keypath,
            node_hash,
            node_type,
            left_child,
            right_child,
            value,
            if_delete_subtrie=False):
        # Keypath prefixes match
        if if_delete_subtrie:
            if len(keypath) < len(left_child) and keypath == left_child[:len(keypath)]:
                return BLANK_HASH
        if keypath[:len(left_child)] == left_child:
            # Recurse into child
            subnode_hash = self._set(
                right_child,
                keypath[len(left_child):],
                value,
                if_delete_subtrie,
            )
            # If child is empty
            if subnode_hash == BLANK_HASH:
                return BLANK_HASH
            subnodetype, sub_left_child, sub_right_child = parse_node(self.db[subnode_hash])
            # If the child is a key-value node, compress together the keypaths
            # into one node
            if subnodetype == KV_TYPE:
                return self._hash_and_save(
                    encode_kv_node(left_child + sub_left_child, sub_right_child)
                )
            else:
                return self._hash_and_save(encode_kv_node(left_child, subnode_hash))
        # Keypath prefixes don't match. Here we will be converting a key-value node
        # of the form (k, CHILD) into a structure of one of the following forms:
        # 1.    (k[:-1], (NEWCHILD, CHILD))
        # 2.    (k[:-1], ((k2, NEWCHILD), CHILD))
        # 3.    (k1, ((k2, CHILD), NEWCHILD))
        # 4.    (k1, ((k2, CHILD), (k2', NEWCHILD))
        # 5.    (CHILD, NEWCHILD)
        # 6.    ((k[1:], CHILD), (k', NEWCHILD))
        # 7.    ((k[1:], CHILD), NEWCHILD)
        # 8.    (CHILD, (k[1:], NEWCHILD))
        else:
            common_prefix_len = get_common_prefix_length(left_child, keypath[:len(left_child)])
            # New key-value pair can not contain empty value
            # Or one can not delete non-exist subtrie
            if not value or if_delete_subtrie:
                return node_hash
            # valnode: the child node that has the new value we are adding
            # Case 1: keypath prefixes almost match, so we are in case (1), (2), (5), (6)
            if len(keypath) == common_prefix_len + 1:
                valnode = self._hash_and_save(encode_leaf_node(value))
            # Case 2: keypath prefixes mismatch in the middle, so we need to break
            # the keypath in half. We are in case (3), (4), (7), (8)
            else:
                if len(keypath) <= common_prefix_len:
                    raise NodeOverrideError(
                        "Fail to set the value because it's key"
                        " is the prefix of other existing key")
                valnode = self._hash_and_save(
                    encode_kv_node(
                        keypath[common_prefix_len + 1:],
                        self._hash_and_save(encode_leaf_node(value)),
                    )
                )
            # oldnode: the child node the has the old child value
            # Case 1: (1), (3), (5), (6)
            if len(left_child) == common_prefix_len + 1:
                oldnode = right_child
            # (2), (4), (6), (8)
            else:
                oldnode = self._hash_and_save(
                    encode_kv_node(left_child[common_prefix_len + 1:], right_child)
                )
            # Create the new branch node (because the key paths diverge, there has to
            # be some "first bit" at which they diverge, so there must be a branch
            # node somewhere)
            if keypath[common_prefix_len:common_prefix_len + 1] == BYTE_1:
                newsub = self._hash_and_save(encode_branch_node(oldnode, valnode))
            else:
                newsub = self._hash_and_save(encode_branch_node(valnode, oldnode))
            # Case 1: keypath prefixes match in the first bit, so we still need
            # a kv node at the top
            # (1) (2) (3) (4)
            if common_prefix_len:
                return self._hash_and_save(
                    encode_kv_node(left_child[:common_prefix_len], newsub)
                )
            # Case 2: keypath prefixes diverge in the first bit, so we replace the
            # kv node with a branch node
            # (5) (6) (7) (8)
            else:
                return newsub

    def _set_branch_node(
            self,
            keypath,
            node_type,
            left_child,
            right_child,
            value,
            if_delete_subtrie=False):
        # Which child node to update? Depends on first bit in keypath
        if keypath[:1] == BYTE_0:
            new_left_child = self._set(left_child, keypath[1:], value, if_delete_subtrie)
            new_right_child = right_child
        else:
            new_right_child = self._set(right_child, keypath[1:], value, if_delete_subtrie)
            new_left_child = left_child
        # Compress branch node into kv node
        if new_left_child == BLANK_HASH or new_right_child == BLANK_HASH:
            subnodetype, sub_left_child, sub_right_child = parse_node(
                self.db[
                    new_left_child
                    if new_left_child != BLANK_HASH
                    else new_right_child]
            )
            first_bit = BYTE_1 if new_right_child != BLANK_HASH else BYTE_0
            # Compress (k1, (k2, NODE)) -> (k1 + k2, NODE)
            if subnodetype == KV_TYPE:
                return self._hash_and_save(
                    encode_kv_node(first_bit + sub_left_child, sub_right_child)
                )
            # kv node pointing to a branch node
            elif subnodetype in (BRANCH_TYPE, LEAF_TYPE):
                return self._hash_and_save(
                    encode_kv_node(
                        first_bit,
                        new_left_child
                        if new_left_child != BLANK_HASH
                        else new_right_child
                    )
                )
        else:
            return self._hash_and_save(encode_branch_node(new_left_child, new_right_child))

    def exists(self, key):
        validate_is_bytes(key)

        return self.get(key) is not None

    def delete(self, key):
        """
        Equals to setting the value to None
        """
        validate_is_bytes(key)

        self.root_hash = self._set(self.root_hash, encode_to_bin(key), b'')

    def delete_subtrie(self, key):
        """
        Given a key prefix, delete the whole subtrie that starts with the key prefix.

        Key will be encoded into binary array format first.

        It will call `_set` with `if_delete_subtrie` set to True.
        """
        validate_is_bytes(key)

        self.root_hash = self._set(
            self.root_hash,
            encode_to_bin(key),
            value=b'',
            if_delete_subtrie=True,
        )

    #
    # Convenience
    #
    @property
    def root_node(self):
        return self.db[self.root_hash]

    @root_node.setter
    def root_node(self, node):
        validate_is_bin_node(node)

        self.root_hash = self._hash_and_save(node)

    #
    # Utils
    #
    def _hash_and_save(self, node):
        """
        Saves a node into the database and returns its hash
        """
        validate_is_bin_node(node)

        node_hash = keccak(node)
        self.db[node_hash] = node
        return node_hash

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
