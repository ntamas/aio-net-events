from anyio import Condition, create_task_group, from_thread, to_thread
from contextlib import asynccontextmanager
from functools import partial

from .portable import PortableNetworkEventDetectorBackend

__all__ = ("SystemConfigurationBasedNetworkEventDetectorBackend",)


class SystemConfigurationBasedNetworkEventDetectorBackend(
    PortableNetworkEventDetectorBackend
):
    """Specialized network event detector backend for macOS using the
    SystemConfiguration framework.

    This backend works similarly to the PortableNetworkEventDetectorBackend_,
    but it uses an SCDynamicStore instance to detect changes to network
    interfaces and addresses instead of polling the network configuration.

    This backend is preferred by the autodetection mechanism on macOS over the
    default portable backend.
    """

    def __init__(self) -> None:
        super().__init__()
        self._condition = None

    @asynccontextmanager
    async def use(self) -> None:
        self._ensure_condition_exists()
        async with create_task_group() as tg:
            tg.start_soon(
                partial(to_thread.run_sync, self._run_worker_thread, cancellable=True)
            )
            yield

    def _ensure_condition_exists(self) -> None:
        """Creates the condition object that the backend will use to notify
        listeners about network change events.

        This function is used to avoid having to create a condition object
        in the constructor, which may be executed outside the context of an
        event loop.
        """
        if self._condition is None:
            self._condition = Condition()

    def _on_network_changed(self, *args, **kwds):
        """Callback that is called by the SystemConfiguration framework when
        the network configuration has changed.

        This function runs in the context of the worker thread.
        """
        from_thread.run(self._on_network_changed_main)

    async def _on_network_changed_main(self):
        """Task that is scheduled on the main event loop when the network
        configuration has changed.

        This function runs in the context of the main event loop.
        """
        async with self._condition:
            await self._condition.notify_all()

    def _run_worker_thread(self):
        """Runs the worker thread that waits for network events."""
        from Foundation import (
            CFRunLoopAddSource,
            CFRunLoopGetCurrent,
            kCFRunLoopCommonModes,
            CFRunLoopRun,
        )
        from SystemConfiguration import (
            SCDynamicStoreCreate,
            SCDynamicStoreSetNotificationKeys,
            SCDynamicStoreCreateRunLoopSource,
        )

        store = SCDynamicStoreCreate(
            None, "global-network-watcher", self._on_network_changed, None
        )
        SCDynamicStoreSetNotificationKeys(
            store, None, ["State:/Network/Global/IPv4", "State:/Network/Global/IPv6"]
        )

        CFRunLoopAddSource(
            CFRunLoopGetCurrent(),
            SCDynamicStoreCreateRunLoopSource(None, store, 0),
            kCFRunLoopCommonModes,
        )

        CFRunLoopRun()

    async def wait_until_next_scan(self) -> None:
        self._ensure_condition_exists()
        async with self._condition:
            await self._condition.wait()
