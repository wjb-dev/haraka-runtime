import pytest
import asyncio
import signal

from src.haraka_runtime.core.interfaces import Adapter
from src.haraka_runtime.orchestrator.orchestrator import Orchestrator, LifecycleState


# ────────────────────────────────────────────────────────────────────────────
# Dummy adapter for mark_ready tests
# ────────────────────────────────────────────────────────────────────────────
class ReadyAdapter(Adapter):
    def __init__(self, name: str, ready_after: float, runtime: Orchestrator = None):
        self.name = name
        # runtime will be overwritten by orch.use(), but accept it here for clarity
        self.runtime = runtime
        self._ready_after = ready_after

    async def startup(self):
        # Simulate async setup then mark ready in orchestrator
        await asyncio.sleep(self._ready_after)
        self.runtime.mark_ready(self.name)

    async def shutdown(self):
        pass


# ────────────────────────────────────────────────────────────────────────────
# Tests for wait_for_all_ready
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wait_for_all_ready_completes():
    """
    Two Adapters mark themselves ready after a short delay;
    wait_for_all_ready should return without error once both
    have run startup().
    """
    orch = Orchestrator()

    svc1 = ReadyAdapter("svc1", ready_after=0.01, runtime=orch)
    svc2 = ReadyAdapter("svc2", ready_after=0.02, runtime=orch)
    orch.use(svc1, priority=1)
    orch.use(svc2, priority=1)

    # Actually invoke their startup methods so mark_ready() is called
    task1 = asyncio.create_task(svc1.startup())
    task2 = asyncio.create_task(svc2.startup())

    # Now wait_for_all_ready will observe both events being set
    await orch.wait_for_all_ready(timeout=1.0)

    # Clean up
    await task1
    await task2


@pytest.mark.asyncio
async def test_wait_for_all_ready_times_out():
    """
    An Adapter never signals ready; wait_for_all_ready should time out.
    """
    orch = Orchestrator()

    class NeverReady(Adapter):
        def __init__(self, name: str):
            self.name = name

        async def startup(self):
            # Do nothing (never calls mark_ready)
            await asyncio.sleep(0)

        async def shutdown(self):
            pass

    svc = NeverReady("never")
    orch.use(svc, priority=1)

    with pytest.raises(asyncio.TimeoutError):
        await orch.wait_for_all_ready(timeout=0.1)


# ──────────────────────────────────────────────────────────────────────────────
# Test for UNIX signal handling
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_signal_handler_triggers_shutdown(monkeypatch):
    """
    Directly invoking _on_signal should schedule shutdown()
    and transition state to DESTROYED, with a log entry.
    """
    orch = Orchestrator()

    called = False

    async def fake_shutdown():
        nonlocal called
        called = True
        orch.state = LifecycleState.DESTROYED

    # Patch orchestrator.shutdown
    monkeypatch.setattr(orch, "shutdown", fake_shutdown)

    # Simulate receiving SIGINT
    orch._on_signal(signal.SIGINT)
    # Allow the loop to schedule the shutdown task
    await asyncio.sleep(0)

    assert called is True
    assert orch.state == LifecycleState.DESTROYED
