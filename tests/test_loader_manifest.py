import sys
import yaml
import pytest

from src.haraka_runtime.core.interfaces import Adapter
from src.haraka_runtime.loader.manifest_loader import load_adapter_from_manifest
from src.haraka_runtime.orchestrator.orchestrator import Orchestrator, Settings, DocsProvider


# Constants for dummy module
DUMMY_MODULE_NAME = "dummy_adapter_module"
DUMMY_CLASS_NAME = "DummyAdapter"

@pytest.fixture(autouse=True)
def dummy_adapter_module(tmp_path, monkeypatch):
    """
    Create a temporary module that defines DummyAdapter, a subclass of Adapter.
    """
    # Write dummy_adapter_module.py
    module_path = tmp_path / f"{DUMMY_MODULE_NAME}.py"
    module_source = f'''
from src.haraka_runtime.core.interfaces import Adapter

class {DUMMY_CLASS_NAME}(Adapter):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.name = kwargs.get("name", "{DUMMY_MODULE_NAME}")

    async def startup(self):
        pass

    async def shutdown(self):
        pass
'''
    module_path.write_text(module_source)

    # Prepend tmp_path to sys.path for import
    monkeypatch.syspath_prepend(str(tmp_path))
    # Ensure no stale import
    if DUMMY_MODULE_NAME in sys.modules:
        del sys.modules[DUMMY_MODULE_NAME]
    yield


def test_load_valid_adapter(tmp_path):
    """
    Given a valid manifest, load_adapter_from_manifest should instantiate the adapter,
    register it in the orchestrator with correct priority and dependencies,
    and pass settings to constructor.
    """
    # Prepare manifest
    manifest = {
        "entrypoint": f"{DUMMY_MODULE_NAME}:{DUMMY_CLASS_NAME}",
        "settings": {"name": "svc1", "foo": "bar"},
        "priority": 42,
        "dependencies": ["dep1", "dep2"]
    }
    manifest_path = tmp_path / "adapter.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest))

    orch = Orchestrator()
    svc = load_adapter_from_manifest(manifest_path, orch)

    # Assertions
    assert isinstance(svc, Adapter)
    assert svc.__class__.__name__ == DUMMY_CLASS_NAME
    # Registry check
    reg_svc, pri, deps = orch._registry[svc.name]
    assert reg_svc is svc
    assert pri == 42
    assert deps == ["dep1", "dep2"]
    # Constructor settings
    settings_dict = getattr(svc, "kwargs", {})
    assert settings_dict.get("foo") == "bar"
    assert svc.name == "svc1"


def test_missing_entrypoint_raises_value_error(tmp_path):
    """
    If manifest lacks 'entrypoint', expect ValueError.
    """
    manifest = {"settings": {}}
    manifest_path = tmp_path / "adapter.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest))

    orch = Orchestrator()
    with pytest.raises(ValueError) as exc_info:
        load_adapter_from_manifest(manifest_path, orch)
    assert "Missing 'entrypoint'" in str(exc_info.value)


def test_import_error_for_bad_module_or_class(tmp_path):
    """
    If entrypoint references a non-existent module/class, expect ImportError.
    """
    manifest = {"entrypoint": "no_such_mod:NoClass"}
    manifest_path = tmp_path / "adapter.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest))

    orch = Orchestrator()
    with pytest.raises(ImportError):
        load_adapter_from_manifest(manifest_path, orch)


def test_type_error_for_non_adapter_class(tmp_path, monkeypatch):
    """
    If entrypoint points to a class not subclassing Adapter, expect TypeError.
    """
    # Create module with class NotAnAdapter
    bad_mod = tmp_path / "bad_module.py"
    bad_mod.write_text("""
class NotAnAdapter:
    pass
""")
    monkeypatch.syspath_prepend(str(tmp_path))
    if "bad_module" in sys.modules:
        del sys.modules["bad_module"]

    manifest = {"entrypoint": "bad_module:NotAnAdapter"}
    manifest_path = tmp_path / "adapter.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest))

    orch = Orchestrator()
    with pytest.raises(TypeError) as exc_info:
        load_adapter_from_manifest(manifest_path, orch)
    assert "does not implement the Adapter interface" in str(exc_info.value)


def test_loader_uses_default_priority_and_deps(tmp_path):
    """
    If manifest omits 'priority' and 'dependencies', defaults of 0 and [] are used.
    """
    manifest = {
        "entrypoint": f"{DUMMY_MODULE_NAME}:{DUMMY_CLASS_NAME}",
        "settings": {"name": "svc2"}
        # priority and dependencies omitted
    }
    manifest_path = tmp_path / "adapter.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest))

    orch = Orchestrator()
    svc = load_adapter_from_manifest(manifest_path, orch)

    reg_svc, pri, deps = orch._registry[svc.name]
    assert pri == 0  # default
    assert deps == []  # default
