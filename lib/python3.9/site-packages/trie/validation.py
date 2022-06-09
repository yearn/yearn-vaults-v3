from trie.constants import (
    BLANK_NODE,
    BLANK_HASH,
    BINARY_TRIE_NODE_TYPES
)
from trie.exceptions import (
    ValidationError,
)


def validate_is_bytes(value):
    if not isinstance(value, bytes):
        raise ValidationError("Value is not of type `bytes`: got '{0}'".format(type(value)))


def validate_length(value, length):
    if len(value) != length:
        raise ValidationError("Value is of length {0}.  Must be {1}".format(len(value), length))


def validate_is_node(node):
    if node == BLANK_NODE:
        return
    elif len(node) == 2:
        key, value = node
        validate_is_bytes(key)
        if isinstance(value, list):
            validate_is_node(value)
        else:
            validate_is_bytes(value)
    elif len(node) == 17:
        validate_is_bytes(node[16])
        for sub_node in node[:16]:
            if sub_node == BLANK_NODE:
                continue
            elif isinstance(sub_node, list):
                validate_is_node(sub_node)
            else:
                validate_is_bytes(sub_node)
                validate_length(sub_node, 32)
    else:
        raise ValidationError("Invalid Node: {0}".format(node))


def validate_is_bin_node(node):
    if node == BLANK_HASH or node[0] in BINARY_TRIE_NODE_TYPES:
        return
    else:
        raise ValidationError("Invalid Node: {0}".format(node))
