"""Interface specification for network event detector backends."""

from abc import abstractmethod, ABCMeta
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any, Dict, List

__all__ = ("NetworkEventDetectorBackend",)

NetworkInterface = Any


class NetworkEventDetectorBackend(metaclass=ABCMeta):
    """Interface specification for network event detector backends."""

    def configure(self, configuration: Dict[str, Any]) -> None:
        """Configures the detector backend and specifies what the backend should
        report.

        The format of the configuration dictionary depends on the backend.
        The default implementation does nothing.

        It is guaranteed that no one else holds a reference to the configuration
        dictionary so it is safe to just store it as-is (without making a
        copy first).
        """
        pass  # pragma: no cover

    @abstractmethod
    async def get_addresses(self, interface: NetworkInterface) -> Dict[int, List[Any]]:
        """Returns all known addresses for a given network interface.

        Returns:
            a dictionary mapping address family identifiers (typically numbers)
            to lists of corresponding network addresses. It is guaranteed to be
            an instance that the caller can freely modify.
        """
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def key_of(self, interface: NetworkInterface) -> str:
        """Returns a unique key for a network interface that can be used for
        identity comparisons.

        The string does not have to be human-readable, but it must be unique
        for each network interface.
        """
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    async def scan(self) -> List[NetworkInterface]:
        """Scans the system for network interfaces and returns the list of
        interfaces found.
        """
        raise NotImplementedError  # pragma: no cover

    @asynccontextmanager
    async def use(self) -> AsyncIterator[None]:
        """Async context manager that is entered when the backend starts up and
        exits when the backend shuts down.

        This context manager can be used to run background tc_genhreads or manage
        any additional resources that correspond to the lifetime of the backend.

        The default implementation does nothing.
        """
        yield

    @abstractmethod
    async def wait_until_next_scan(self) -> None:
        """Async function that blocks until the next scan is due.

        It is up to the backend to decide whether it scans the network
        interfaces regularly or whether it uses some underlying mechanism of the
        OS to detect events.
        """
        raise NotImplementedError  # pragma: no cover
