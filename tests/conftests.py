# tests/conftest.py
# Ensure the project root directory is in sys.path so the orchestrator
# module can be imported

import sys
from pathlib import Path

# Compute the project root (one level up from this tests/ folder)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
