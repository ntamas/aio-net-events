"""Portable network event detector backend based on `netifaces` and
continuous polling.
"""

from anyio import sleep
from typing import Any, Dict, List

from .base import NetworkEventDetectorBackend, NetworkInterface


class PortableNetworkEventDetectorBackend(NetworkEventDetectorBackend):
    """Portable network event detector backend based on `netifaces` and
    continuous polling.
    """

    def __init__(self):
        """Constructor."""
        import netifaces

        self._netifaces = netifaces

    async def get_addresses(self, interface: NetworkInterface) -> Dict[int, List[Any]]:
        addresses = self._netifaces.ifaddresses(interface)
        return {
            family: [item.get("addr") for item in addr_for_family]
            for family, addr_for_family in addresses.items()
        }

    def key_of(self, interface: NetworkInterface) -> str:
        return str(interface)

    async def scan(self) -> List[NetworkInterface]:
        return self._netifaces.interfaces()

    async def wait_until_next_scan(self) -> None:
        await sleep(1)
