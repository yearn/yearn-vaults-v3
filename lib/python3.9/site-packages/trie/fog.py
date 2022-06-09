import ast
from itertools import zip_longest
from typing import (
    Any,
    Dict,
    Iterable,
    Sequence,
    Tuple,
)

from eth_utils import (
    to_tuple,
    ValidationError,
)
from sortedcontainers import SortedSet

from trie.exceptions import (
    FullDirectionalVisibility,
    PerfectVisibility,
)
from trie.typing import (
    GenericSortedSet,
    HexaryTrieNode,
    Nibbles,
    NibblesInput,
)
from trie.utils.nibbles import (
    decode_nibbles,
    encode_nibbles,
)
from trie.utils.nodes import (
    key_starts_with,
)


class HexaryTrieFog:
    """
    Keeps track of which parts of a trie have been verified to exist.

    Named after "fog of war" popular in video games like... Red Alert? IDK, I'm old.

    Object is immutable. Any changes, like marking a key prefix as complete, will
    return a new HexaryTrieFog object.
    """
    _unexplored_prefixes: GenericSortedSet[Nibbles]

    # INVARIANT: No unexplored prefix may start with another unexplored prefix
    #   For example, _unexplored_prefixes may not be {(1, 2), (1, 2, 3)}.

    def __init__(self) -> None:
        # Always start without knowing anything about a trie. The only unexplored
        #   prefix is the root prefix: (), which means the whole trie is unexplored.
        self._unexplored_prefixes = SortedSet({()})

    def __repr__(self) -> str:
        return f"HexaryTrieFog<{self._unexplored_prefixes!r}>"

    @property
    def is_complete(self) -> bool:
        return len(self._unexplored_prefixes) == 0

    def explore(
            self,
            old_prefix_input: NibblesInput,
            foggy_sub_segments: Sequence[NibblesInput]) -> 'HexaryTrieFog':
        """
        The fog lifts from the old prefix. This call returns a HexaryTrieFog that narrows
        down the unexplored key prefixes. from the old prefix to the indicated children.

        For example, if only the key prefix 0x12 is unexplored, then calling
        explore((1, 2), ((3,), (0xe, 0xf))) would mark large swaths of 0x12 explored, leaving only
        two prefixes as unknown: 0x123 and 0x12ef. To continue exploring those prefixes, navigate
        to them using traverse() or traverse_from().

        The sub_segments_input may be empty, which means the old prefix has been fully explored.
        """
        old_prefix = Nibbles(old_prefix_input)
        sub_segments = [Nibbles(segment) for segment in foggy_sub_segments]
        new_fog_prefixes = self._unexplored_prefixes.copy()

        try:
            new_fog_prefixes.remove(old_prefix)
        except KeyError:
            raise ValidationError(f"Old parent {old_prefix} not found in {new_fog_prefixes!r}")

        if len(set(sub_segments)) != len(sub_segments):
            raise ValidationError(
                f"Got duplicate sub_segments in {sub_segments} to HexaryTrieFog.explore()"
            )

        # Further validation that no segment is a prefix of another
        all_lengths = set(len(segment) for segment in sub_segments)
        if len(all_lengths) > 1:
            # The known use case of exploring nodes one at a time will never arrive in this
            #   validation check which might be slow. Leaf nodes have no sub segments,
            #   extension nodes have exactly one, and branch nodes have all sub_segments
            #   of length 1. If a new use case hits this verification, and speed becomes an issue,
            #   see https://github.com/ethereum/py-trie/issues/107
            for segment in sub_segments:
                shorter_lengths = [length for length in all_lengths if length < len(segment)]
                for check_length in shorter_lengths:
                    trimmed_segment = segment[:check_length]
                    if trimmed_segment in sub_segments:
                        raise ValidationError(
                            f"Cannot add {segment} which is a child of segment {trimmed_segment}"
                        )

        new_fog_prefixes.update([old_prefix + segment for segment in sub_segments])
        return self._new_trie_fog(new_fog_prefixes)

    def mark_all_complete(self, prefix_inputs: Sequence[NibblesInput]) -> 'HexaryTrieFog':
        """
        These might be leaves, or prefixes with 0 unknown keys within the range.

        This is equivalent to the following, but with better performance:

            result_fog = old_fog
            for complete_prefix in prefixes:
                result_fog = result_fog.explore(complete_prefix, ())
        """
        new_unexplored_prefixes = self._unexplored_prefixes.copy()
        for prefix in map(Nibbles, prefix_inputs):
            if prefix not in new_unexplored_prefixes:
                raise ValidationError(
                    f"When marking {prefix} complete, could not find in {new_unexplored_prefixes!r}"
                )

            new_unexplored_prefixes.remove(prefix)
        return self._new_trie_fog(new_unexplored_prefixes)

    def nearest_unknown(self, key_input: NibblesInput = ()) -> Nibbles:
        """
        Find the foggy prefix that is nearest to the supplied key.

        If prefixes are exactly the same distance to the left and right,
        then return the prefix on the right.

        :raises PerfectVisibility: if there are no foggy prefixes remaining
        """
        key = Nibbles(key_input)

        index = self._unexplored_prefixes.bisect(key)

        if index == 0:
            # If sorted set is empty, bisect will return 0
            # But it might also return 0 if the search value is lower than the lowest existing
            try:
                return self._unexplored_prefixes[0]
            except IndexError as exc:
                raise PerfectVisibility("There are no more unexplored prefixes") from exc
        elif index == len(self._unexplored_prefixes):
            return self._unexplored_prefixes[-1]
        else:
            nearest_left = self._unexplored_prefixes[index - 1]
            nearest_right = self._unexplored_prefixes[index]

            # is the left or right unknown prefix closer?
            left_distance = self._prefix_distance(nearest_left, key)
            right_distance = self._prefix_distance(key, nearest_right)
            if left_distance < right_distance:
                return nearest_left
            else:
                return nearest_right

    def nearest_right(self, key_input: NibblesInput) -> Nibbles:
        """
        Find the foggy prefix that is nearest on the right to the supplied key.

        :raises PerfectVisibility: if there are no foggy prefixes to the right
        """
        key = Nibbles(key_input)

        index = self._unexplored_prefixes.bisect(key)

        if index == 0:
            # If sorted set is empty, bisect will return 0
            # But it might also return 0 if the search value is lower than the lowest existing
            try:
                return self._unexplored_prefixes[0]
            except IndexError as exc:
                raise PerfectVisibility("There are no more unexplored prefixes") from exc
        else:
            nearest_left = self._unexplored_prefixes[index - 1]

            # always return nearest right, unless prefix of key is unexplored
            if key_starts_with(key, nearest_left):
                return nearest_left
            else:
                try:
                    # This can raise a IndexError if index == len(unexplored prefixes)
                    return self._unexplored_prefixes[index]
                except IndexError as exc:
                    raise FullDirectionalVisibility(
                        f"There are no unexplored prefixes to the right of {key}"
                    ) from exc

    @staticmethod
    @to_tuple
    def _prefix_distance(low_key: Nibbles, high_key: Nibbles) -> Iterable[int]:
        """
        How far are the two keys from each other, as a sequence of differences.
        The first non-zero distance must be positive, but the remaining distances may
        be negative. Distances are designed to be simply compared, like distance1 < distance2.

        The high_key must be higher than the low key, or the output distances are not
        guaranteed to be accurate.
        """
        for low_nibble, high_nibble in zip_longest(low_key, high_key, fillvalue=None):
            if low_nibble is None:
                final_low_nibble = 15
            else:
                final_low_nibble = low_nibble

            if high_nibble is None:
                final_high_nibble = 0
            else:
                final_high_nibble = high_nibble

            # Note: this might return a negative value. It's fine, because only the
            #   relative distance matters. For example (1, 2) and (2, 1) produce a
            #   distance of (1, -1). If the other reference point is (3, 1), making
            #   the distance to the middle (1, 0), then the "correct" thing happened.
            #   The (1, 2) key is a tiny bit closer to the (2, 1) key, and a tuple
            #   comparison of the distance will show it as a smaller distance.
            yield final_high_nibble - final_low_nibble

    @classmethod
    def _new_trie_fog(cls, unexplored_prefixes: SortedSet) -> 'HexaryTrieFog':
        """
        Convert a set of unexplored prefixes to a proper HexaryTrieFog object.
        """
        copy = cls()
        copy._unexplored_prefixes = unexplored_prefixes
        return copy

    def serialize(self) -> bytes:
        # encode nibbles to a bytes value, to compress this down a bit
        prefixes = [
            encode_nibbles(nibbles)
            for nibbles in self._unexplored_prefixes
        ]
        return f"HexaryTrieFog:{prefixes!r}".encode()

    @classmethod
    def deserialize(cls, encoded: bytes) -> 'HexaryTrieFog':
        serial_prefix = b'HexaryTrieFog:'
        if not encoded.startswith(serial_prefix):
            raise ValueError(f"Cannot deserialize this into HexaryTrieFog object: {encoded!r}")
        else:
            encoded_list = encoded[len(serial_prefix):]
            prefix_list = ast.literal_eval(encoded_list.decode())
            deserialized_prefixes = SortedSet(
                # decode nibbles from compressed bytes value, and validate each value in range(16)
                Nibbles(decode_nibbles(prefix))
                for prefix in prefix_list
            )
            return cls._new_trie_fog(deserialized_prefixes)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, HexaryTrieFog):
            return False
        else:
            return self._unexplored_prefixes == other._unexplored_prefixes


class TrieFrontierCache:
    """
    Keep a cache of HexaryTrieNodes for use with traverse_from. This
    can be used neatly with HexaryTrieFog to only keep a cache of the frontier
    of unexplored nodes, so that every expansion into a new unexplored node requires
    only one database lookup instead of log(n).
    """
    def __init__(self) -> None:
        self._cache: Dict[Nibbles, Tuple[HexaryTrieNode, Nibbles]] = {}

    def get(self, prefix: NibblesInput) -> Tuple[HexaryTrieNode, Nibbles]:
        """
        Find the cached node body of the parent of the given prefix.

        :return: parent node body, and the path from parent to the given prefix

        :raises KeyError: if there is no cached value for the prefix
        """
        return self._cache[Nibbles(prefix)]

    def add(
            self,
            node_prefix_input: NibblesInput,
            trie_node: HexaryTrieNode,
            sub_segments: Sequence[NibblesInput]) -> None:

        """
        Add a new cached node body for each of the sub segments supplied. Later cache
        lookups will be in the form of get(node_prefix + sub_segments[0]).

        :param node_prefix: the path from the root to the cached node
        :param trie_node: the body to cache
        :param sub_segments: all of the children of the parent which should be made indexable
        """
        node_prefix = Nibbles(node_prefix_input)

        # remove the cache entry for looking up node_prefix as a child
        if node_prefix != ():
            # If the cache entry doesn't exist, we can just ignore its absence
            self._cache.pop(Nibbles(node_prefix), None)

        # add cache entry for each child
        for segment in sub_segments:
            new_prefix = node_prefix + Nibbles(segment)
            self._cache[new_prefix] = (trie_node, Nibbles(segment))

    def delete(self, prefix: NibblesInput) -> None:
        """
        Delete the cache of the parent node for the given prefix. This only deletes
        this prefix's reference to the parent node, not all references to the parent node.
        """
        # If the cache entry doesn't exist, we can just ignore its absence
        self._cache.pop(Nibbles(prefix), None)
