from aio_net_events import choose_backend
from pathlib import Path


def test_autodetection():
    import platform

    backend = choose_backend()

    if platform.system() == "Darwin":
        assert (
            backend.__class__.__name__
            == "SystemConfigurationBasedNetworkEventDetectorBackend"
        )
    elif platform.system() == "Linux" and Path("/proc/net/netlink").exists():
        assert backend.__class__.__name__ == "NetlinkBasedNetworkEventDetectorBackend"
    else:
        assert backend.__class__.__name__ == "PortableNetworkEventDetectorBackend"
