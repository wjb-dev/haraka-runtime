import pytest

from haraka_runtime.core.interfaces import Adapter
from haraka_runtime.orchestrator.orchestrator import Orchestrator


# Dummy adapter implementation for testing
class DummyAdapter(Adapter):
    def __init__(self, name: str, record_list: list):
        self.name = name
        self._record = record_list
        self.runtime = None

    async def startup(self):
        # Record startup invocation
        self._record.append(f"start:{self.name}")

    async def shutdown(self):
        # Record shutdown invocation
        self._record.append(f"stop:{self.name}")


@pytest.mark.asyncio
async def test_registration_records_adapter():
    orch = Orchestrator()
    rec = []
    svc = DummyAdapter("svcTest", rec)

    # Register the adapter with priority and dependencies
    orch.use(svc, priority=7, dependencies=["depX", "depY"])

    # Assert registry contains the adapter
    assert "svcTest" in orch._registry
    registered_adapter, pri, deps = orch._registry["svcTest"]
    assert registered_adapter is svc
    assert pri == 7
    assert deps == ["depX", "depY"]


async def set_up():
    orch = Orchestrator()
    rec = []

    # Define adapters with specific priorities and dependencies
    svc_a = DummyAdapter("A", rec)
    svc_b = DummyAdapter("B", rec)
    svc_c = DummyAdapter("C", rec)

    orch.use(svc_a, priority=10)  # no dependencies
    orch.use(svc_b, priority=5, dependencies=["A"])  # depends on A
    orch.use(svc_c, priority=7)  # no dependencies

    # Run orchestrator
    await orch.run(
        settings=type("S", (), {"port": 0})(), app=type("D", (), {"docs_url": "/"})()
    )
    # Shutdown orchestrator
    await orch.shutdown()

    return rec


@pytest.mark.asyncio
async def test_startup_order_priority_and_deps():
    rec = await set_up()
    # Extract startup calls and verify order
    startup_calls = [r for r in rec if r.startswith("start")]
    assert startup_calls == ["start:A", "start:C", "start:B"]


@pytest.mark.asyncio
async def test_shutdown_order_reverse():
    rec = await set_up()

    # Extract shutdown calls and verify reverse order
    shutdown_calls = [r for r in rec if r.startswith("stop")]
    assert shutdown_calls == ["stop:B", "stop:C", "stop:A"]


def test_circular_dependency_raises():
    orch = Orchestrator()
    # Simulate A -> B -> A dependency
    rec = []
    svc_a = DummyAdapter("A", rec)
    svc_b = DummyAdapter("B", rec)

    orch.use(svc_a, priority=1, dependencies=["B"])
    orch.use(svc_b, priority=1, dependencies=["A"])

    # Directly calling _resolve_start_order should detect the cycle
    with pytest.raises(RuntimeError) as exc:
        orch._resolve_start_order()
    assert "Circular dependency" in str(exc.value)
