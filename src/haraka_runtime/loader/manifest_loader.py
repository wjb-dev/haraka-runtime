import importlib
import yaml
from pathlib import Path
from types import ModuleType

from src.haraka_runtime.core.interfaces import Adapter
from src.haraka_runtime.orchestrator.orchestrator import Orchestrator


def load_adapter_from_manifest(path: Path, runtime: Orchestrator) -> Adapter:
    """
    Load and register an adapter defined by a adapter.yaml file.

    Args:
        path (Path): Path to the adapter.yaml file
        runtime (Orchestrator): The Haraka Runtime instance

    Returns:
        Adapter: Instantiated and registered adapter
    """
    manifest = yaml.safe_load(path.read_text())

    if not manifest.get("entrypoint"):
        raise ValueError(f"Missing 'entrypoint' in manifest: {path}")

    module_path, class_name = manifest["entrypoint"].split(":")
    try:
        module: ModuleType = importlib.import_module(module_path)
        cls = getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import adapter: {manifest['entrypoint']}") from e

    if not issubclass(cls, Adapter):
        raise TypeError(f"{class_name} does not implement the Adapter interface")

    adapter = cls(**manifest.get("settings", {}))

    runtime.use(
        adapter,
        priority=manifest.get("priority", 0),
        dependencies=manifest.get("dependencies", [])
    )
    return adapter
