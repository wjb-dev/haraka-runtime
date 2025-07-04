import re
import logging
from pathlib import Path
import socket

from mypy import api as mypy_api

from src.haraka_runtime.orchestrator.orchestrator import (
    Orchestrator,
    Settings,
    DocsProvider,
)


# ──────────────────────────────────────────────────────────────────────────────
# Test for docs URL printing
# ──────────────────────────────────────────────────────────────────────────────


def test_print_docs_url_formats_correctly(caplog, monkeypatch):
    """
    Ensure _print_docs_url logs both localhost and network URLs correctly.
    """
    orch = Orchestrator()

    # Replace its custom logger with a standard one caplog can capture
    std_logger = logging.getLogger("test_logger")
    std_logger.setLevel(logging.INFO)
    # Remove any existing handlers and add a simple stream handler
    std_logger.handlers.clear()
    std_logger.addHandler(logging.StreamHandler())
    orch.logger = std_logger

    # Define fake instances satisfying the Protocols
    class FakeSettings(Settings):
        port: int = 1234

    class FakeApp(DocsProvider):
        docs_url: str = "/foo"

    settings = FakeSettings()
    app = FakeApp()

    caplog.set_level(logging.INFO, logger="test_logger")

    # Now when _print_docs_url calls orch.logger.info(), caplog will catch it
    orch._print_docs_url(settings, app)

    # Collect captured messages
    messages = [rec.getMessage() for rec in caplog.records]

    # Validate localhost URL
    assert any(
        "Swagger UI available at: http://localhost:1234/foo" in msg for msg in messages
    ), f"Localhost log not found in: {messages}"

    # Validate network URL (dynamic host)
    host = socket.gethostbyname(socket.gethostname()).replace(".", r"\.")
    pattern = rf"Network Swagger UI available at: http://{host}:1234/foo"
    assert any(
        re.search(pattern, msg) for msg in messages
    ), f"Network log not found in: {messages}"


# ──────────────────────────────────────────────────────────────────────────────
# Meta-test for type hints
# ──────────────────────────────────────────────────────────────────────────────


def test_type_hints_present():
    """
    Run mypy on orchestrator file to ensure zero type errors.
    """
    # Compute path to orchestrator.py
    root = Path(__file__).parent.parent
    orchestrator_file = str(
        root / "src" / "haraka_runtime" / "orchestrator" / "orchestrator.py"
    )
    result = mypy_api.run([orchestrator_file, "--ignore-missing-imports"])
    stdout, stderr, exit_status = result
    assert exit_status == 0, f"mypy errors:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
