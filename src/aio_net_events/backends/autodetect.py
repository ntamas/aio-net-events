from .base import NetworkEventDetectorBackend


def choose_backend() -> NetworkEventDetectorBackend:
    """Chooses an appropriate network event detector backend for the current
    platform when invoked with no arguments.

    Returns:
        a newly constructed network event detector backend instance
    """
    from .portable import PortableNetworkEventDetectorBackend

    return PortableNetworkEventDetectorBackend()
