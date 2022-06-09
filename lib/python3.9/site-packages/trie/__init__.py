import pkg_resources

from .binary import (  # noqa: F401
    BinaryTrie,
)
from .hexary import (  # noqa: F401
    HexaryTrie,
)


__version__ = pkg_resources.get_distribution("trie").version
