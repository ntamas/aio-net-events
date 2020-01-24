from anyio import sleep, wait_socket_readable
from os import getpid

from .portable import PortableNetworkEventDetectorBackend


RTMGRP_LINK = 1
RTMGRP_IPV4_IFADDR = 0x10
RTMGRP_IPV6_IFADDR = 0x100
RTMGRP_DECnet_IFADDR = 0x1000


class NetlinkBasedNetworkEventDetectorBackend(PortableNetworkEventDetectorBackend):
    """Specialized network event detector backend for Linux with netlink support.

    This backend works similarly to the PortableNetworkEventDetectorBackend_,
    but it uses a netlink socket to detect changes to network interfaces and
    addresses instead of polling the network configuration.

    This backend is preferred by the autodetection mechanism on Linux over the
    default portable backend if it detects that netlink support is enabled in
    the kernel.
    """

    def __init__(self):
        """Constructor."""
        super().__init__()

        from socket import socket, AF_NETLINK, SOCK_RAW, NETLINK_ROUTE

        self._socket = socket(AF_NETLINK, SOCK_RAW, NETLINK_ROUTE)
        self._socket.bind(
            (
                getpid(),
                RTMGRP_LINK
                | RTMGRP_IPV4_IFADDR
                | RTMGRP_IPV6_IFADDR
                | RTMGRP_DECnet_IFADDR,
            )
        )
        self._socket.setblocking(0)

    def __del__(self):
        self._socket.close()

    async def wait_until_next_scan(self) -> None:
        await wait_socket_readable(self._socket)
        while True:
            try:
                data = self._socket.recv(4096)
                if not data:
                    break
            except BlockingIOError:
                break
            await sleep(0)
