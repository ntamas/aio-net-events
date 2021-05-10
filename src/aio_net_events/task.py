"""Async event detector for network interfaces."""

from anyio import Event
from collections import namedtuple
from contextlib import contextmanager
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, Optional, Tuple

from .backends.base import NetworkEventDetectorBackend, NetworkInterface
from .backends.autodetect import choose_backend


__all__ = ("NetworkEventDetector",)


class NetworkEventType(Enum):
    """Enum representing the possible network event types."""

    INTERFACE_ADDED = "interface_added"
    INTERFACE_REMOVED = "interface_removed"
    ADDRESS_ADDED = "address_added"
    ADDRESS_REMOVED = "address_removed"


NetworkEvent = namedtuple("NetworkEvent", "type interface address_family address key")
NetworkEventDetectorEntry = namedtuple(
    "NetworkEventDetectorEntry", "interface key addresses"
)


class NetworkEventDetector:
    """Network event detector class.

    This class continuously scans the system for network interfaces and dispatches
    events when network interfaces are added or removed, or when a network
    interface gains a new IP address or loses an existing one.
    """

    def __init__(
        self,
        params: Optional[Dict] = None,
        *,
        backend: Callable[[], NetworkEventDetectorBackend] = choose_backend
    ):
        """Constructor.

        Parameters:
            params: dictionary of keyword arguments to pass to the
                `configure()` method of the backend in order to specify what
                sort of interfaces we are interested in.
            backend: a callable that returns an instance of NetworkEventScannerBackend_
                when invoked with no arguments; defaults to autodetection
                depending on the current platform.
        """
        self._backend = backend

        self._params = self._preprocess_params(dict(params or {}))
        self._entries = {}

        self._suspended = 0
        self._resume_event = None

    async def added_addresses(self) -> AsyncIterator[NetworkEvent]:
        """Runs the network event detection in an asynchronous task.

        Yields:
            event objects describing the network addresses that were added and
            the corresponding network interfaces
        """
        async for event in self.events():
            if event.type == NetworkEventType.ADDRESS_ADDED:
                yield event

    async def added_interfaces(self) -> AsyncIterator[NetworkInterface]:
        """Runs the network event detection in an asynchronous task.

        Yields:
            network interface objects, one for each interface whose addition was
            detected. Removed network interfaces are not reported.
        """
        async for event in self.events():
            if event.type == NetworkEventType.INTERFACE_ADDED:
                yield event.interface

    async def changed_addresses(self) -> AsyncIterator[NetworkEvent]:
        """Runs the network event detection in an asynchronous task.

        Yields:
            event objects describing the network addresses that were added or
            removed and the corresponding network interfaces
        """
        async for event in self.events():
            if event.type in (
                NetworkEventType.ADDRESS_ADDED,
                NetworkEventType.ADDRESS_REMOVED,
            ):
                yield event

    async def events(self) -> AsyncIterator[NetworkEvent]:
        """Runs the network event detection in an asynchronous task.

        Yields:
            event objects describing the network interfaces or addresses that
            were added or removed
        """
        backend = self._backend() if callable(self._backend) else self._backend
        backend.configure(self._params)
        key_of = backend.key_of

        async with backend.use():
            while True:
                if self._suspended:
                    await self._resume_event.wait()

                interfaces = await backend.scan()

                added = {}
                changed = {}

                for index, interface in enumerate(interfaces):
                    addresses = await backend.get_addresses(interface)
                    key = key_of(interface)

                    entry = self._entries.get(key)
                    if entry is not None:
                        changed[key] = self._compare_addresses(entry, addresses)
                        if any(changed[key]):
                            self._entries[key] = entry = entry._replace(
                                addresses=addresses
                            )
                    else:
                        entry = added[key] = NetworkEventDetectorEntry(
                            interface=interface, addresses=addresses, key=key
                        )

                to_remove = [key for key in self._entries.keys() if key not in changed]
                removed = [self._entries.pop(key) for key in to_remove]
                self._entries.update(added)

                for entry in removed:
                    interface = entry.interface
                    key = entry.key

                    for family, addresses in entry.addresses.items():
                        for address in addresses:
                            event = NetworkEvent(
                                type=NetworkEventType.ADDRESS_REMOVED,
                                interface=interface,
                                key=key,
                                address=address,
                                address_family=family,
                            )
                            yield event

                    event = NetworkEvent(
                        type=NetworkEventType.INTERFACE_REMOVED,
                        interface=interface,
                        key=key,
                        address=None,
                        address_family=None,
                    )
                    yield event

                for key, (added_entries, removed_entries) in changed.items():
                    for entry in removed_entries:
                        interface, key, family, address = entry
                        event = NetworkEvent(
                            type=NetworkEventType.ADDRESS_REMOVED,
                            interface=interface,
                            key=key,
                            address=address,
                            address_family=family,
                        )
                        yield event

                    for entry in added_entries:
                        interface, key, family, address = entry
                        event = NetworkEvent(
                            type=NetworkEventType.ADDRESS_ADDED,
                            interface=interface,
                            key=key,
                            address=address,
                            address_family=family,
                        )
                        yield event

                for entry in added.values():
                    interface = entry.interface
                    key = entry.key

                    event = NetworkEvent(
                        type=NetworkEventType.INTERFACE_ADDED,
                        interface=interface,
                        key=key,
                        address=None,
                        address_family=None,
                    )
                    yield event

                    for family, addresses in entry.addresses.items():
                        for address in addresses:
                            event = NetworkEvent(
                                type=NetworkEventType.ADDRESS_ADDED,
                                interface=interface,
                                key=key,
                                address=address,
                                address_family=family,
                            )
                            yield event

                await backend.wait_until_next_scan()

    async def removed_addresses(self) -> AsyncIterator[NetworkEvent]:
        """Runs the network event detection in an asynchronous task.

        Yields:
            event objects describing the network addresses that were removed and
            the corresponding network interfaces
        """
        async for event in self.events():
            if event.type == NetworkEventType.ADDRESS_REMOVED:
                yield event

    async def removed_interfaces(self) -> AsyncIterator[NetworkEvent]:
        """Runs the network event detection in an asynchronous task.

        Yields:
            network interface objects, one for each interface whose removal was
            detected. Added interfaces are not reported.
        """
        async for event in self.events():
            if event.type == NetworkEventType.INTERFACE_REMOVED:
                yield event.interface

    def resume(self) -> None:
        """Resumes the network event detector task after a suspension."""
        self._suspended -= 1
        if not self._suspended and self._resume_event:
            self._resume_event.set()

    def suspend(self) -> None:
        """Temporarily suspends the network event detector."""
        self._suspended += 1
        if self._suspended and not self._resume_event:
            self._resume_event = Event()

    @contextmanager
    def suspended(self) -> None:
        """Async context manager that suspends the network event detector while the
        execution is in the context.
        """
        self.suspend()
        try:
            yield
        finally:
            self.resume()

    @staticmethod
    def _compare_addresses(
        entry: NetworkEventDetectorEntry, new: Dict[int, Any]
    ) -> Tuple:
        """Compares a set of old addresses with a set of new addresses for a
        network interface, and reports the differences.

        Parameters:
            entry: the entry in the state object of the network event detector
                that contains the old addresses we have found at the last scan
            new: a dictionary mapping address families to the new addresses

        Returns:
            a tuple consisting of the list of added addresses and the list of
            removed addresses. Each entry in these lists consists of four
            items: interface, key of interface, address family and address
        """
        old = entry.addresses

        added, removed = [], []

        for family in set(list(old.keys()) + list(new.keys())):
            old_addresses = old.get(family)
            new_addresses = new.get(family)

            if old_addresses == new_addresses:
                # Nothing changed, good
                pass
            elif old_addresses is None:
                # The whole address family was added
                added.extend(
                    (entry.interface, entry.key, family, address)
                    for address in new_addresses
                )
            elif new_addresses is None:
                # The whole address family was removed
                removed.extend(
                    (entry.interface, entry.key, family, address)
                    for address in old_addresses
                )
            else:
                old_addresses, new_addresses = set(old_addresses), set(new_addresses)
                added.extend(
                    (entry.interface, entry.key, family, address)
                    for address in new_addresses - old_addresses
                )
                removed.extend(
                    (entry.interface, entry.key, family, address)
                    for address in old_addresses - new_addresses
                )

        return added, removed

    @staticmethod
    def _preprocess_params(params: Dict) -> Dict:
        """Preprocesses the parameters passed to the constructor.

        Currently a no-op.

        Parameters:
            params: the dictionary to process. It will be modified in-place.

        Returns:
            the same dictionary that was passed in
        """
        return params
