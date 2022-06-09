from typing import List, Optional

import requests
from cid import make_cid  # type: ignore
from pydantic import AnyUrl

from .base import BaseModel
from .utils import CONTENT_ADDRESSED_SCHEMES, Algorithm, Hex, compute_checksum


class Compiler(BaseModel):
    name: str
    version: str
    settings: Optional[dict] = None
    contractTypes: Optional[List[str]] = None


class Checksum(BaseModel):
    """Checksum information about the contents of a source file."""

    algorithm: Algorithm
    hash: Hex


class Source(BaseModel):
    """Information about a source file included in a Package Manifest."""

    urls: List[AnyUrl] = []
    """Array of urls that resolve to the same source file."""

    checksum: Optional[Checksum] = None
    """Hash of the source file. Per EIP-2678,
    this field is only necessary if source must be fetched."""

    content: Optional[str] = None
    """Inlined contract source."""

    installPath: Optional[str] = None
    """Filesystem path of source file."""
    # NOTE: This was probably done for solidity, needs files cached to disk for compiling
    #       If processing a local project, code already exists, so no issue
    #       If processing remote project, cache them in ape project data folder

    type: Optional[str] = None
    """The type of the source file."""

    license: Optional[str] = None
    """The type of license associated with this source file."""

    references: Optional[List[str]] = None  # NOTE: Not a part of canonical EIP-2678 spec
    """List of `Source` objects that depend on this object."""
    # TODO: Add `SourceId` type and use instead of `str`

    imports: Optional[List[str]] = None  # NOTE: Not a part of canonical EIP-2678 spec
    """List of source objects that this object depends on."""
    # TODO: Add `SourceId` type and use instead of `str`

    def fetch_content(self) -> str:
        """
        Fetch the content for the given Source object.
        Loads resource at ``urls`` into ``content`` if not available.

        Returns:
            str
        """

        # NOTE: This is a trapdoor to bypass fetching logic if already available
        if self.content:
            return self.content

        if len(self.urls) == 0:
            raise ValueError("No content to fetch.")

        for url in map(str, self.urls):
            # TODO: Have more robust handling of IPFS URIs
            if url.startswith("ipfs"):
                url = url.replace("ipfs://", "https://ipfs.io/ipfs/")

            response = requests.get(url)
            if response.status_code == 200:
                return response.text

        raise ValueError("Could not fetch content.")

    def calculate_checksum(self, algorithm: Algorithm = Algorithm.MD5) -> Checksum:
        """
        Compute the checksum of the ``Source`` object.
        Will shortcircuit to content identifier if using content-addressed file references
        Fails if ``content`` isn't available locally or by fetching.

        Args:
            algorithm (`Optional[~ethpm_types.utils.Algorithm]`): The algorithm to use to compute
              the checksum with. Defaults to MD5.

        Returns:
            :class:`~ethpm_types.source.Checksum`
        """

        # NOTE: Content-addressed URI schemes have checksum encoded directly in address.
        for url in self.urls:
            if url.scheme in CONTENT_ADDRESSED_SCHEMES:
                # TODO: Pull algorithm for checksum calc from codec
                cid = make_cid(url.host)
                return Checksum(hash=cid.multihash.hex(), algorithm=Algorithm.SHA256)

        content = self.fetch_content()
        return Checksum(
            hash=compute_checksum(content.encode("utf8"), algorithm=algorithm),
            algorithm=algorithm,
        )

    def content_is_valid(self) -> bool:
        """
        Return if content is corrupted.
        Will never be corrupted if content is locally available.
        If content is referenced by content addressed identifier,
        will not be corrupted either.
        If referenced from a server URL,
        then checksum must be present and will be validated against.

        Returns:
            bool
        """

        # NOTE: Per EIP-2678, checksum is not needed if content does not need to be fetched
        if self.content:
            return True

        # NOTE: Per EIP-2678, Checksum is not required if a URL is content addressed.
        #       This is because the act of fetching the content validates the checksum.
        for url in self.urls:
            if url.scheme in CONTENT_ADDRESSED_SCHEMES:
                return True

        if self.checksum:
            return self.checksum == self.calculate_checksum(algorithm=self.checksum.algorithm)

        return False
