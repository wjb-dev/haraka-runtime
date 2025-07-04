"""
Sample Adapter
==============

A minimal example adapter implementation for the Haraka Adapter SDK.
Implements the Adapter interface with no-op startup and shutdown methods.
"""

import asyncio
from core.interfaces import Adapter


class SampleAdapter(Adapter):
    """
    A no-op sample adapter for demonstrating SDK usage.

    Attributes:
        name (str): Unique adapter name used by the orchestrator.
    """

    name: str = "sample_adapter"

    async def startup(self) -> None:
        """
        Start up the adapter.

        This method is called by the orchestrator when loading the adapter.
        Use this hook to initialize connections or resources.
        """
        print(f"Starting {self.name}")

    async def shutdown(self) -> None:
        """
        Shut down the adapter.

        This method is called by the orchestrator during graceful shutdown.
        Use this hook to release resources cleanly.
        """
        print(f"Shutting down {self.name}")


async def main() -> None:
    """
    Entry point for running the adapter standalone.

    Instantiates the adapter, runs startup, then shutdown.
    """
    adapter = SampleAdapter()
    await adapter.startup()
    await adapter.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
