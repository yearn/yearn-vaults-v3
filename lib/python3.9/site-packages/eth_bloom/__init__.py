import sys

from .bloom import BloomFilter  # noqa: F401


if sys.version_info < (3, 5):
    raise EnvironmentError("Python 3.5 or above is requires")
