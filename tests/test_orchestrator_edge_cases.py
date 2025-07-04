import asyncio
import logging
import signal
import socket

import pytest

from haraka_runtime.core.interfaces import Adapter
from haraka_runtime.orchestrator.orchestrator import Orchestrator, LifecycleState, DocsProvider, Settings


class DummyAdapter(Adapter):
    """Minimal adapter stub with runtime injected dynamically."""
    def __init__(self, name):
        self.name = name
        self.start_called = False
        self.stop_called = False

    async def startup(self):
        self.start_called = True

    async def shutdown(self):
        self.stop_called = True


class FakeSettings(Settings):
    port = 1234


class FakeApp(DocsProvider):
    docs_url = "/foo"


@pytest.fixture
def orch(caplog):
    # Create a plain Python logger for capture
    logger = logging.getLogger("test_orch")
    logger.setLevel(logging.DEBUG)               # ← allow debug logs
    logger.handlers.clear()
    logger.addHandler(logging.StreamHandler())

    # Tell caplog to capture DEBUG and above for our logger
    caplog.set_level(logging.DEBUG, logger="test_orch")

    orch = Orchestrator()
    orch.logger = logger
    return orch

def test_use_registers_adapter_and_warns_on_duplicate(orch, caplog):
    svc = DummyAdapter("A")
    orch.use(svc)  # deps=None should default to []
    assert "A" in orch._registry
    # duplicate registration
    orch.use(svc)
    assert any("already registered" in rec.getMessage() for rec in caplog.records)


def test_mark_ready_logs_info_first_and_debug_on_repeat_and_warns_unknown(orch, caplog):
    # unknown adapter
    orch.mark_ready("nope")
    assert any("unknown adapter 'nope'" in rec.getMessage() for rec in caplog.records)
    # mark twice
    svc = DummyAdapter("B")
    orch.use(svc)
    orch.mark_ready("B")
    orch.mark_ready("B")
    # first log is INFO, second is DEBUG
    msgs = [rec.levelname for rec in caplog.records if "B" in rec.getMessage()]
    assert "INFO" in msgs
    assert "DEBUG" in msgs


def test_wait_for_all_ready_completes_when_all_marked_and_times_out_if_not(orch):    # happy path
    svc1 = DummyAdapter("X"); svc2 = DummyAdapter("Y")
    orch.use(svc1); orch.use(svc2)
    # mark ready immediately
    orch.mark_ready("X"); orch.mark_ready("Y")
    # should not raise
    asyncio.run(orch.wait_for_all_ready(timeout=0.1))

    # timeout path
    orch2 = Orchestrator()
    svc3 = DummyAdapter("Z")
    orch2.use(svc3)
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(orch2.wait_for_all_ready(timeout=0.0))


def test__resolve_start_order_raises_on_unknown_and_circular_and_sorts_by_priority(orch):
    # unknown dependency
    svc = DummyAdapter("A")
    orch.use(svc, dependencies=["missing"])
    with pytest.raises(RuntimeError):
        orch._resolve_start_order()

    # circular dependency
    a = DummyAdapter("a"); b = DummyAdapter("b")
    orch2 = Orchestrator()
    orch2.use(a, dependencies=["b"])
    orch2.use(b, dependencies=["a"])
    with pytest.raises(RuntimeError):
        orch2._resolve_start_order()

    # priority ordering
    orch3 = Orchestrator()
    a = DummyAdapter("a"); b = DummyAdapter("b"); c = DummyAdapter("c")
    orch3.use(a, priority=1)
    orch3.use(b, priority=10)
    orch3.use(c, priority=5, dependencies=["a"])
    order = orch3._resolve_start_order()
    # b(10) first, then a(1)->c(5) depends on a so a then c
    assert [svc.name for svc in order] == ["b", "c", "a"]


def test_run_and_shutdown_warns_on_reentry_and_shutdown_before_run(orch, caplog):
    settings = FakeSettings(); app = FakeApp()

    # shutdown before run
    asyncio.run(orch.shutdown())
    assert any("Not running or already destroyed" in rec.getMessage() for rec in caplog.records)

    # run once
    orch_single = Orchestrator()
    # **use the test logger so caplog can capture**
    orch_single.logger = orch.logger

    svc = DummyAdapter("one")
    orch_single.use(svc)
    asyncio.run(orch_single.run(settings, app))

    # second run should warn
    asyncio.run(orch_single.run(settings, app))
    assert any("Already started or shut down" in rec.getMessage() for rec in caplog.records)


@pytest.mark.asyncio
async def test__on_signal_schedules_shutdown_and_logs(orch, caplog, monkeypatch):
    # Swap in our fake shutdown
    called = False
    async def fake_shutdown():
        nonlocal called
        called = True
    monkeypatch.setattr(orch, "shutdown", fake_shutdown)

    # Now _on_signal will schedule fake_shutdown() on the current loop
    orch._on_signal(signal.SIGTERM)

    # Give the loop a tick to actually run the task
    await asyncio.sleep(0)

    assert called is True
    assert any("initiating shutdown" in rec.getMessage() for rec in caplog.records)


@pytest.mark.asyncio
async def test__wrap_task_propagates_exceptions_and_logs_failure(orch, caplog):
    # wire in the test logger so caplog can capture
    logger = logging.getLogger("test_orch")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.addHandler(logging.StreamHandler())
    caplog.set_level(logging.DEBUG, logger="test_orch")
    orch.logger = logger

    # 2) exception path: a coroutine that raises
    async def fails():
        raise ValueError("oops")

    with pytest.raises(ValueError):
        # directly await the wrapper to re-raise
        await orch._wrap_task(fails)

    assert any("Task fails failed:" in rec.getMessage() for rec in caplog.records)

@pytest.mark.asyncio
async def test__wrap_task_handles_cancellation_and_logs_message(orch, caplog):
    # 1) swap in a simple logger that caplog will catch
    logger = logging.getLogger("test_cancel")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.addHandler(logging.StreamHandler())
    caplog.set_level(logging.DEBUG, logger="test_cancel")
    orch.logger = logger

    # 2) define a coroutine that never completes
    async def never_finishes():
        await asyncio.Future()

    # 3) schedule the wrapper and then immediately cancel
    wrapper_task = asyncio.create_task(orch._wrap_task(never_finishes))
    await asyncio.sleep(0)  # give the wrapper a chance to start and enter its await
    wrapper_task.cancel()  # now cancel it

    # 4) give the loop a tick so that the cancellation handler runs
    await asyncio.sleep(0)

    # 5) assert that our wrapper logged a cancellation message
    assert any("cancelled" in rec.getMessage().lower() for rec in caplog.records)


def test__print_docs_url_logs_urls_on_success_and_warns_on_error(orch, caplog, monkeypatch):
    settings = FakeSettings(); app = FakeApp()
    # success
    orch._print_docs_url(settings, app)
    assert any("Swagger UI available" in rec.getMessage() for rec in caplog.records)

    # failure branch: monkeypatch socket to raise
    class BadSocket:
        @staticmethod
        def gethostbyname(x): raise OSError("no host")
    monkeypatch.setattr(socket, "gethostbyname", BadSocket.gethostbyname)
    caplog.clear()
    orch._print_docs_url(settings, app)
    assert any("Failed to determine docs URL" in rec.getMessage() for rec in caplog.records)
