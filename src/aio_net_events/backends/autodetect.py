import platform

from pathlib import Path

from .base import NetworkEventDetectorBackend


def choose_backend() -> NetworkEventDetectorBackend:
    """Chooses an appropriate network event detector backend for the current
    platform when invoked with no arguments.

    Returns:
        a newly constructed network event detector backend instance
    """
    if platform.system() == "Linux" and Path("/proc/net/netlink").exists():
        from .netlink import NetlinkBasedNetworkEventDetectorBackend

        return NetlinkBasedNetworkEventDetectorBackend()
    elif platform.system() == "Darwin":
        from .macos import SystemConfigurationBasedNetworkEventDetectorBackend

        return SystemConfigurationBasedNetworkEventDetectorBackend()
    else:
        from .portable import PortableNetworkEventDetectorBackend

        return PortableNetworkEventDetectorBackend()
