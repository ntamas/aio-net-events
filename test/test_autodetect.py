from aio_net_events import choose_backend


def test_autodetection():
    backend = choose_backend()
    assert backend.__class__.__name__ == "PortableNetworkEventDetectorBackend"
