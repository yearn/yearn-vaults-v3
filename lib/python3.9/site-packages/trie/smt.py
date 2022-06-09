from typing import (
    Dict,
    Sequence,
    Tuple,
)

from eth_utils import (
    keccak,
    to_int,
)

from eth_typing import (
    Hash32,
)

from trie.constants import (
    BLANK_NODE,
)

from trie.exceptions import (
    ValidationError,
)

from trie.validation import (
    validate_is_bytes,
    validate_length,
)


def calc_root(key: bytes, value: bytes, branch: Sequence[Hash32]) -> Hash32:
    """
    Obtain the merkle root of a given key/value/branch set.
    Can be used to validate a merkle proof or compute it's value from data.

    :param key: the keypath to decide the ordering of the sibling nodes in the branch
    :param value: the value (or leaf) that starts the merkle proof computation
    :param branch: the sequence of sibling nodes used to recursively perform the computation

    :return: the root hash of the merkle proof computation

    .. doctest::

        >>> key = b'\x02'  # Keypath
        >>> value = b''  # Value (or leaf)
        >>> branch = tuple([b'\x00'] * 8)  # Any list of hashes
        >>> calc_root(key, value, branch)
        b'.+4IKt[\xd2\x14\xe4).\xf5\xc6\n\x11=\x01\xe89\xa1Z\x07#\xfd~(;\xfb\xb8\x8a\x0e'

    """
    validate_is_bytes(key)
    validate_is_bytes(value)
    validate_length(branch, len(key)*8)

    path = to_int(key)
    target_bit = 1
    # traverse the path in leaf->root order
    # branch is in root->leaf order (key is in MSB to LSB order)
    node_hash = keccak(value)
    for sibling_node in reversed(branch):
        if path & target_bit:
            node_hash = keccak(sibling_node + node_hash)
        else:
            node_hash = keccak(node_hash + sibling_node)
        target_bit <<= 1

    return node_hash


class SparseMerkleProof:
    """
    Track the current value and merkle proof branch for a given key.
    This will enable the tracked proof data to stay up to date with changes
    that may be streamed to the end user over external protocols without having
    to interactively query the full SMT to obtain the most up-to-date branch.

    Attributes:
        key: key we are tracking
        value: currently synchronized value
        branch: currently synchronized merkle proof branch
        root_hash: result of computing the merkle root for the tracked data

    .. doctest::

        >>> # smt is located on another process or machine
        >>> smt = SparseMerkleTree(key_size=1)
        >>> our_key = b'\x03'
        >>> our_value = b'\x01'
        >>> smt.set(our_key, our_value)
        >>> # We need to track proof data for *some* reason
        >>> our_proof = SparseMerkleProof(our_key, our_value, smt.branch(our_key))
        >>> their_key = b'\x05'
        >>> their_new_value = b'\x01'
        >>> their_node_updates = smt.set(their_key, their_new_value)
        >>> # tree updates can be communicated over any channel to proof obj
        >>> our_proof.update(their_key, their_new_value, their_node_updates)
        >>> # Note our branch data was never queried from smt to our proof obj
        >>> our_proof.branch == smt.branch(our_key)
        True
        >>> # Despite that, root hashes are kept consistent. Proof validates!
        >>> our_proof.root_hash == smt.root_hash
        True
        >>> # This works for multiple updates
        >>> our_proof.update(their_key, b'\x02', smt.set(their_key, b'\x02'))
        >>> our_proof.update(their_key, b'\x03', smt.set(their_key, b'\x03'))
        >>> our_proof.update(their_key, b'\x04', smt.set(their_key, b'\x04'))
        >>> our_proof.root_hash == smt.root_hash
        True
        >>> # This also works for updates to ourselves
        >>> our_proof.update(our_key, b'\x05', smt.set(our_key, b'\x05'))
        >>> our_proof.root_hash == smt.root_hash
        True
        >>> our_proof.value
        b'\x05'

    """

    def __init__(self, key: bytes, value: bytes, branch: Sequence[Hash32]):
        validate_is_bytes(key)
        validate_is_bytes(value)
        validate_length(branch, len(key)*8)

        self._key = key
        self._key_size = len(key)
        self._value = value
        self._branch = list(branch)  # Avoid issues with mutable lists
        self._branch_size = len(branch)

    @property
    def key(self) -> bytes:
        return self._key

    @property
    def value(self) -> bytes:
        return self._value

    @property
    def branch(self) -> Tuple[Hash32]:
        return tuple(self._branch)

    @property
    def root_hash(self) -> Hash32:
        return calc_root(self.key, self.value, self.branch)

    def update(self, key: bytes, value: bytes, node_updates: Sequence[Hash32]):
        """
        Merge an update for another key with the one we are tracking internally.

        :param key: keypath of the update we are processing
        :param value: value of the update we are processing
        :param node_updates: sequence of sibling nodes (in root->leaf order)
                             must be at least as large as the first diverging
                             key in the keypath

        """
        validate_is_bytes(key)
        validate_length(key, self._key_size)

        # Path diff is the logical XOR of the updated key and this account
        path_diff = (to_int(self.key) ^ to_int(key))

        # Same key (diff of 0), update the tracked value
        if path_diff == 0:
            self._value = value
            # No need to update branch
        else:
            # Find the first mismatched bit between keypaths. This is
            # where the branch point occurs, and we should update the
            # sibling node in the source branch at the branch point.
            # NOTE: Keys are in MSB->LSB (root->leaf) order.
            #       Node lists are in root->leaf order.
            #       Be sure to convert between them effectively.
            for bit in reversed(range(self._branch_size)):
                if path_diff & (1 << bit) > 0:
                    branch_point = (self._branch_size - 1) - bit
                    break

            # NOTE: node_updates only has to be as long as necessary
            #       to obtain the update. This allows an optimization
            #       of pruning updates to the maximum possible depth
            #       that would be required to update, which may be
            #       significantly smaller than the tree depth.
            if len(node_updates) <= branch_point:
                raise ValidationError("Updated node list is not deep enough")

            # Update sibling node in the branch where our key differs from the update
            self._branch[branch_point] = node_updates[branch_point]
            # No need to update value


class SparseMerkleTree:

    def __init__(self,
                 key_size: int = 32,
                 default: bytes = BLANK_NODE):
        """
        Maintain a a binary trie with a particular depth (defined by key size)
        All values are stored at that depth, and the tree has a default value that it is
        reset to when a key is cleared. If this default is anything other than a blank
        node, then all keys "exist" in the database, which mimics the behavior of Ethereum
        on-chain datastores.

        :param key_size: The size (in # of bytes) of the key. All keys must be this size.
                         Note that the size should be between 1 and 32 bytes. For performance,
                         it is not advisible to have a key larger than 32 bytes (and you should
                         optimize to much less than that) but if the data structure you seek
                         to use as a key is larger, the suggestion would be to hash that
                         structure in a serialized format to obtain the key, or add a unique
                         identifier to the structure.
        :param default: The default value used for the database. Initializes the root.
        """
        # Ensure we can support the given depth
        if not 1 <= key_size <= 32:
            raise ValidationError("Keysize must be number of bytes in range [1, 32]")

        self._key_size = key_size  # key's size (# of bytes)
        self.depth = key_size * 8  # depth is number of bits in the key

        self._default = default

        # Initialize an empty tree with one branch
        self.db = {}
        node = self._default  # Default leaf node
        for _ in range(self.depth):
            node_hash = keccak(node)
            self.db[node_hash] = node
            node = node_hash + node_hash

        # Finally, write the root hash
        self.root_hash = keccak(node)
        self.db[self.root_hash] = node

    @classmethod
    def from_db(
            cls,
            db: Dict[bytes, bytes],
            root_hash: Hash32,
            key_size: int = 32,
            default: bytes = BLANK_NODE):
        smt = cls(key_size=key_size, default=default)

        # If db is provided, and is not consistent,
        # there may be a silent error. Can't solve that easily.
        smt.db = db

        # Set root_hash, so we know where to start
        validate_is_bytes(root_hash)
        validate_length(root_hash, 32)  # Must be a bytes32 hash

        smt.root_hash = root_hash

        return smt

    def get(self, key: bytes) -> bytes:
        value, _ = self._get(key)

        # Ensure that it isn't blank!
        if value == BLANK_NODE:
            raise KeyError("Key does not exist")

        return value

    def branch(self, key: bytes) -> Tuple[Hash32]:
        value, branch = self._get(key)

        # Ensure that it isn't blank!
        if value == BLANK_NODE:
            raise KeyError("Key does not exist")

        return branch

    def _get(self, key: bytes) -> Tuple[bytes, Tuple[Hash32]]:
        """
        Returns db value and branch in root->leaf order
        """
        validate_is_bytes(key)
        validate_length(key, self._key_size)
        branch = []

        target_bit = 1 << (self.depth - 1)
        path = to_int(key)
        node_hash = self.root_hash
        # Append the sibling node to the branch
        # Iterate on the parent
        for _ in range(self.depth):
            node = self.db[node_hash]
            left, right = node[:32], node[32:]
            if path & target_bit:
                branch.append(left)
                node_hash = right
            else:
                branch.append(right)
                node_hash = left
            target_bit >>= 1

        # Value is the last hash in the chain
        # NOTE: Didn't do exception here for testing purposes
        return self.db[node_hash], tuple(branch)

    def set(self, key: bytes, value: bytes) -> Tuple[Hash32]:
        """
        Returns all updated hashes in root->leaf order
        """
        validate_is_bytes(key)
        validate_length(key, self._key_size)
        validate_is_bytes(value)

        path = to_int(key)
        node = value
        _, branch = self._get(key)
        proof_update = []  # Keep track of proof updates

        target_bit = 1
        # branch is in root->leaf order, so flip
        for sibling_node in reversed(branch):
            # Set
            node_hash = keccak(node)
            proof_update.append(node_hash)
            self.db[node_hash] = node

            # Update
            if (path & target_bit):
                node = sibling_node + node_hash
            else:
                node = node_hash + sibling_node

            target_bit <<= 1

        # Finally, update root hash
        self.root_hash = keccak(node)
        self.db[self.root_hash] = node

        # updates need to be in root->leaf order, so flip back
        return tuple(reversed(proof_update))

    def exists(self, key: bytes) -> bool:
        validate_is_bytes(key)
        validate_length(key, self._key_size)

        try:
            self.get(key)
            return True
        except KeyError:
            return False

    def delete(self, key: bytes) -> Tuple[Hash32]:
        """
        Equals to setting the value to None
        Returns all updated hashes in root->leaf order
        """
        validate_is_bytes(key)
        validate_length(key, self._key_size)

        return self.set(key, self._default)

    #
    # Dictionary API
    #

    def __getitem__(self, key: bytes) -> bytes:
        return self.get(key)

    def __setitem__(self, key: bytes, value: bytes):
        self.set(key, value)

    def __delitem__(self, key: bytes):
        self.delete(key)

    def __contains__(self, key: bytes) -> bool:
        return self.exists(key)
