import rlp

from trie.constants import (
    NODE_TYPE_BLANK,
    NODE_TYPE_LEAF,
    NODE_TYPE_EXTENSION,
    NODE_TYPE_BRANCH,
    BLANK_NODE,
    KV_TYPE,
    BRANCH_TYPE,
    LEAF_TYPE,
    KV_TYPE_PREFIX,
    BRANCH_TYPE_PREFIX,
    LEAF_TYPE_PREFIX,
)
from trie.exceptions import (
    InvalidNode,
    ValidationError,
)
from trie.utils.binaries import (
    encode_from_bin_keypath,
    decode_to_bin_keypath,
)
from trie.typing import (
    HexaryTrieNode,
    Nibbles,
    RawHexaryNode,
)
from trie.validation import (
    validate_length,
    validate_is_bytes,
)
from .nibbles import (
    decode_nibbles,
    encode_nibbles,
    is_nibbles_terminated,
    add_nibbles_terminator,
    remove_nibbles_terminator,
)


def get_node_type(node):
    if node == BLANK_NODE:
        return NODE_TYPE_BLANK
    elif len(node) == 2:
        key, _ = node
        nibbles = decode_nibbles(key)
        if is_nibbles_terminated(nibbles):
            return NODE_TYPE_LEAF
        else:
            return NODE_TYPE_EXTENSION
    elif len(node) == 17:
        return NODE_TYPE_BRANCH
    else:
        raise InvalidNode("Unable to determine node type")


def is_blank_node(node):
    return node == BLANK_NODE


def is_leaf_node(node):
    if len(node) != 2:
        return False
    key, _ = node
    nibbles = decode_nibbles(key)
    return is_nibbles_terminated(nibbles)


def is_extension_node(node):
    if len(node) != 2:
        return False
    key, _ = node
    nibbles = decode_nibbles(key)
    return not is_nibbles_terminated(nibbles)


def is_branch_node(node):
    return len(node) == 17


def decode_node(encoded_node_or_hash):
    if encoded_node_or_hash == BLANK_NODE:
        return BLANK_NODE
    elif isinstance(encoded_node_or_hash, list):
        return encoded_node_or_hash
    else:
        return rlp.decode(encoded_node_or_hash)


def extract_key(node):
    prefixed_key, _ = node
    key = remove_nibbles_terminator(decode_nibbles(prefixed_key))
    return key


def compute_leaf_key(nibbles):
    return encode_nibbles(add_nibbles_terminator(nibbles))


def compute_extension_key(nibbles):
    return encode_nibbles(nibbles)


def get_common_prefix_length(left_key, right_key):
    for idx, (left_nibble, right_nibble) in enumerate(zip(left_key, right_key)):
        if left_nibble != right_nibble:
            return idx
    return min(len(left_key), len(right_key))


def consume_common_prefix(left_key, right_key):
    common_prefix_length = get_common_prefix_length(left_key, right_key)
    common_prefix = left_key[:common_prefix_length]
    left_remainder = left_key[common_prefix_length:]
    right_remainder = right_key[common_prefix_length:]
    return common_prefix, left_remainder, right_remainder


def key_starts_with(full_key, partial_key):
    if len(full_key) < len(partial_key):
        return False
    else:
        return all(left == right for left, right in zip(full_key, partial_key))


# Binary Trie node utils
def parse_node(node):
    """
    Input: a serialized node
    """
    if node is None or node == b'':
        raise InvalidNode("Blank node is not a valid node type in Binary Trie")
    elif node[0] == BRANCH_TYPE:
        if len(node) != 65:
            raise InvalidNode("Invalid branch node, both child node should be 32 bytes long each")
        # Output: node type, left child, right child
        return BRANCH_TYPE, node[1:33], node[33:]
    elif node[0] == KV_TYPE:
        if len(node) <= 33:
            raise InvalidNode("Invalid kv node, short of key path or child node hash")
        # Output: node type, keypath: child
        return KV_TYPE, decode_to_bin_keypath(node[1:-32]), node[-32:]
    elif node[0] == LEAF_TYPE:
        if len(node) == 1:
            raise InvalidNode("Invalid leaf node, can not contain empty value")
        # Output: node type, None, value
        return LEAF_TYPE, None, node[1:]
    else:
        raise InvalidNode("Unable to parse node")


def encode_kv_node(keypath, child_node_hash):
    """
    Serializes a key/value node
    """
    if keypath is None or keypath == b'':
        raise ValidationError("Key path can not be empty")
    validate_is_bytes(keypath)
    validate_is_bytes(child_node_hash)
    validate_length(child_node_hash, 32)
    return KV_TYPE_PREFIX + encode_from_bin_keypath(keypath) + child_node_hash


def encode_branch_node(left_child_node_hash, right_child_node_hash):
    """
    Serializes a branch node
    """
    validate_is_bytes(left_child_node_hash)
    validate_length(left_child_node_hash, 32)
    validate_is_bytes(right_child_node_hash)
    validate_length(right_child_node_hash, 32)
    return BRANCH_TYPE_PREFIX + left_child_node_hash + right_child_node_hash


def encode_leaf_node(value):
    """
    Serializes a leaf node
    """
    validate_is_bytes(value)
    if value is None or value == b'':
        raise ValidationError("Value of leaf node can not be empty")
    return LEAF_TYPE_PREFIX + value


def annotate_node(node_body: RawHexaryNode) -> HexaryTrieNode:
    """
    Normalize the raw node body to a HexaryTrieNode, for external consumption.
    """
    node_type = get_node_type(node_body)
    if node_type == NODE_TYPE_LEAF:
        return HexaryTrieNode(
            sub_segments=(),
            value=bytes(node_body[-1]),
            suffix=Nibbles(extract_key(node_body)),
            raw=node_body,
        )
    elif node_type == NODE_TYPE_BRANCH:
        sub_segments = tuple(
           Nibbles((nibble,))
           for nibble in range(16) if bool(node_body[nibble])
        )
        return HexaryTrieNode(
            sub_segments=sub_segments,
            value=bytes(node_body[-1]),
            suffix=Nibbles(()),
            raw=node_body,
        )
    elif node_type == NODE_TYPE_EXTENSION:
        key_extension = extract_key(node_body)
        return HexaryTrieNode(
            sub_segments=(Nibbles(key_extension), ),
            value=b'',
            suffix=Nibbles(()),
            raw=node_body,
        )
    elif node_type == NODE_TYPE_BLANK:
        # empty trie
        return HexaryTrieNode(
            sub_segments=(),
            value=b'',
            suffix=Nibbles(()),
            raw=node_body,
        )
    else:
        raise NotImplementedError()
