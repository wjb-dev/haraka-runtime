import pytest
from types import SimpleNamespace

from examples.sample_adapter.app.main import SampleAdapter
from examples.sample_adapter.app.main import main as adapter_main



@pytest.mark.asyncio
async def test_adapter_lifecycle_methods(capsys):
    """
    Ensure the adapter's standalone startup and shutdown print messages.
    """
    adapter = SampleAdapter()
    await adapter.startup()
    captured = capsys.readouterr()
    assert "Starting sample_adapter" in captured.out

    await adapter.shutdown()
    captured = capsys.readouterr()
    assert "Shutting down sample_adapter" in captured.out


@pytest.mark.asyncio
async def test_run_and_shutdown_integration(orchestrator, adapter, capsys):
    """
    Ensure orchestrator.run and shutdown call the adapter's lifecycle hooks.
    """
    settings = SimpleNamespace(port=9000)

    class DummyApp:
        docs_url = "/"

    app = DummyApp()

    await orchestrator.run(settings, app)
    captured = capsys.readouterr()
    assert "Starting sample_adapter" in captured.out

    await orchestrator.shutdown()
    captured = capsys.readouterr()
    assert "Shutting down sample_adapter" in captured.out


def test_duplicate_registration(orchestrator, adapter):
    """
    Registering the same adapter twice does not create duplicates.
    """
    orchestrator.use(adapter, priority=1)
    assert list(orchestrator._registry.keys()).count(adapter.name) == 1

@pytest.mark.asyncio
async def test_main_function_invokes_lifecycle(capsys):
    """
    Calling the module’s `main()` coroutine should start and then shut down the adapter,
    printing both messages once each.
    """
    # Run the main() entrypoint
    await adapter_main()

    # Capture stdout
    captured = capsys.readouterr()
    out = captured.out.strip().splitlines()
    # We expect exactly two lines in order
    assert out == [
        "Starting sample_adapter",
        "Shutting down sample_adapter",
    ]
