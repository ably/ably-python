"""
VCDiff Plugin for Ably Python SDK

This module provides a production-ready VCDiff decoder plugin using the vcdiff library.
It implements the VCDiffDecoder interface.

Usage:
    from ably import VCDiffPlugin, AblyRealtime

    # Create VCDiff plugin
    plugin = VCDiffPlugin()

    # Create client with plugin
    client = AblyRealtime(key="your-key", vcdiff_decoder=plugin)

    # Get channel with delta enabled
    channel = client.channels.get("test", {"delta": "vcdiff"})
"""

import logging

from ably.types.options import VCDiffDecoder
from ably.util.exceptions import AblyException

log = logging.getLogger(__name__)


class VCDiffPlugin(VCDiffDecoder):
    """
    Production VCDiff decoder plugin using Ably's vcdiff library.

    Raises:
        ImportError: If vcdiff is not installed
        AblyException: If VCDiff decoding fails
    """

    def __init__(self):
        """Initialize the VCDiff plugin.

        Raises:
            ImportError: If vcdiff library is not available
        """
        try:
            import vcdiff
            self._vcdiff = vcdiff
        except ImportError as e:
            log.error("vcdiff library not found. Install with: pip install ably[vcdiff]")
            raise ImportError(
                "VCDiff plugin requires vcdiff library. "
                "Install with: pip install ably[vcdiff]"
            ) from e

    def decode(self, delta: bytes, base: bytes) -> bytes:
        """
        Decode a VCDiff delta against a base payload.

        Args:
            delta: The VCDiff-encoded delta data
            base: The base payload to apply the delta to

        Returns:
            bytes: The decoded message payload

        Raises:
            AblyException: If VCDiff decoding fails (error code 40018)
        """
        if not isinstance(delta, bytes):
            raise TypeError("Delta must be bytes")
        if not isinstance(base, bytes):
            raise TypeError("Base must be bytes")

        try:
            # Use the vcdiff library to decode
            result = self._vcdiff.decode(base, delta)
            return result
        except Exception as e:
            log.error(f"VCDiff decode failed: {e}")
            raise AblyException(f"VCDiff decode failure: {e}", 40018, 40018) from e


# Export for easy importing
__all__ = ['VCDiffPlugin']
