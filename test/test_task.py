from aio_net_events import NetworkEventDetector
from aio_net_events.backends.base import NetworkEventDetectorBackend
from anyio import create_task_group, open_cancel_scope, sleep
from collections import defaultdict
from pytest import fixture, mark
from typing import Dict, List, Optional


class MockBackend(NetworkEventDetectorBackend):
    """Mock backend for testing without having access to real network
    interfaces.
    """

    def __init__(self):
        self._interfaces = defaultdict(lambda: defaultdict(list))
        self.params = {}

    def add(
        self,
        interface: str,
        family: Optional[int] = None,
        address: Optional[str] = None,
    ) -> None:
        if family is not None:
            # Add the address
            addresses = self._interfaces[interface][family]
            if address not in addresses:
                addresses.append(address)
        else:
            # Just trigger the creation of the interface
            self._interfaces[interface]

    def configure(self, params):
        self.params = dict(params)

    async def get_addresses(self, interface: str) -> Dict[int, List[str]]:
        result = self._interfaces.get(interface, None)
        return {k: list(v) for k, v in result.items()} if result else {}

    def key_of(self, interface: str) -> str:
        return interface + "_key"

    def remove(
        self,
        interface: str,
        family: Optional[int] = None,
        address: Optional[str] = None,
    ) -> None:
        if family is None:
            del self._interfaces[interface]
        else:
            self._interfaces[interface][family].remove(address)
            if not self._interfaces[interface][family]:
                del self._interfaces[interface][family]

    async def scan(self) -> List[str]:
        await sleep(0.001)
        return sorted(self._interfaces)

    async def wait_until_next_scan(self) -> None:
        await sleep(0.001)


@fixture
def backend():
    return MockBackend()


@fixture
def events():
    class EventCollector:
        def __init__(self):
            self._items = []

        def add(self, event):
            self._items.append(event)

        def get(self):
            result = list(self._items)
            self._items.clear()
            return result

    return EventCollector()


@mark.anyio
async def test_event_generator(backend, events):
    scanner = NetworkEventDetector(backend=backend)

    async def scenario(end):
        backend.add("foo")
        await sleep(0.003)
        assert events.get() == [("interface_added", "foo", "foo_key", None, None)]

        backend.add("bar")
        backend.add("bar")
        backend.add("bar")
        await sleep(0.003)
        assert events.get() == [("interface_added", "bar", "bar_key", None, None)]

        backend.remove("bar")
        backend.add("baz")
        await sleep(0.003)
        assert sorted(events.get()) == [
            ("interface_added", "baz", "baz_key", None, None),
            ("interface_removed", "bar", "bar_key", None, None),
        ]

        backend.add("foo", 18, "de:ad:be:ef:00:00")
        await sleep(0.003)
        assert events.get() == [
            ("address_added", "foo", "foo_key", 18, "de:ad:be:ef:00:00")
        ]

        backend.add("foo", 18, "de:ad:be:ef:00:00")
        await sleep(0.003)
        assert sorted(events.get()) == []

        backend.remove("foo", 18, "de:ad:be:ef:00:00")
        await sleep(0.003)
        assert events.get() == [
            ("address_removed", "foo", "foo_key", 18, "de:ad:be:ef:00:00")
        ]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.003)
        assert sorted(events.get()) == [
            ("interface_removed", "baz", "baz_key", None, None),
            ("interface_removed", "foo", "foo_key", None, None),
        ]

        backend.add("foo", 18, "de:ad:be:ef:00:00")
        await sleep(0.003)
        assert events.get() == [
            ("interface_added", "foo", "foo_key", None, None),
            ("address_added", "foo", "foo_key", 18, "de:ad:be:ef:00:00"),
        ]

        backend.remove("foo", 18, "de:ad:be:ef:00:00")
        backend.add("foo", 18, "de:ad:be:ef:ca:fe")
        await sleep(0.003)
        assert events.get() == [
            ("address_removed", "foo", "foo_key", 18, "de:ad:be:ef:00:00"),
            ("address_added", "foo", "foo_key", 18, "de:ad:be:ef:ca:fe"),
        ]

        backend.remove("foo")
        await sleep(0.003)
        assert events.get() == [
            ("address_removed", "foo", "foo_key", 18, "de:ad:be:ef:ca:fe"),
            ("interface_removed", "foo", "foo_key", None, None),
        ]

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            async for event in scanner.events():
                events.add(
                    (
                        event.type.value,
                        event.interface,
                        event.key,
                        event.address_family,
                        event.address,
                    )
                )


@mark.anyio
async def test_event_generator_suspension(backend, events):
    scanner = NetworkEventDetector(backend=backend)

    async def scenario(end):
        async with scanner.suspended():
            await sleep(0.003)

            backend.add("foo")
            await sleep(0.003)
            assert events.get() == []

            backend.add("bar")
            backend.add("bar")
            backend.add("bar")
            await sleep(0.003)
            assert events.get() == []

            backend.remove("bar")
            backend.add("baz")
            await sleep(0.003)
            assert events.get() == []

        await sleep(0.003)
        assert sorted(events.get()) == [
            ("interface_added", "baz", "baz_key"),
            ("interface_added", "foo", "foo_key"),
        ]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.003)
        assert sorted(events.get()) == [
            ("interface_removed", "baz", "baz_key"),
            ("interface_removed", "foo", "foo_key"),
        ]

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            async for event in scanner.events():
                events.add((event.type.value, event.interface, event.key))


@mark.anyio
async def test_added_interface_generator(backend, events):
    scanner = NetworkEventDetector(backend=backend)

    async def scenario(end):
        backend.add("foo")
        await sleep(0.003)
        assert events.get() == ["foo"]

        backend.add("bar")
        backend.add("bar")
        backend.add("bar")
        await sleep(0.003)
        assert events.get() == ["bar"]

        backend.remove("bar")
        backend.add("baz")
        await sleep(0.003)
        assert events.get() == ["baz"]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.003)
        assert events.get() == []

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            async for interface in scanner.added_interfaces():
                events.add(interface)


@mark.anyio
async def test_removed_interface_generator(backend, events):
    scanner = NetworkEventDetector(backend=backend)

    async def scenario(end):
        backend.add("foo")
        await sleep(0.003)
        assert events.get() == []

        backend.add("bar")
        backend.add("bar")
        backend.add("bar")
        await sleep(0.003)
        assert events.get() == []

        backend.remove("bar")
        backend.add("baz")
        await sleep(0.003)
        assert events.get() == ["bar"]

        backend.remove("foo")
        backend.remove("baz")
        await sleep(0.003)
        assert sorted(events.get()) == ["baz", "foo"]

        await end()

    async with create_task_group() as tg:
        async with open_cancel_scope() as scope:
            await tg.spawn(scenario, scope.cancel)
            async for interface in scanner.removed_interfaces():
                events.add(interface)
