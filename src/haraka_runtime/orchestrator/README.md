# Haraka Runtime Orchestrator

A reusable core orchestrator that manages service registration, startup/shutdown ordering (via priority and dependencies), UNIX signal handling, and readiness gating—so you can plug in new services consistently without boilerplate.

## Table of Contents

1. [Installation](#installation)  
2. [Quick Start](#quick-start)  
3. [Usage](#usage)  
4. [API Reference](#api-reference)  
5. [Examples](#examples)  
6. [Troubleshooting](#troubleshooting)  
7. [CI Integration](#ci-integration)  

---

## Installation

```bash
pip install -r requirements.txt
```

> Make sure you have `asyncio`, `PyYAML`, `fastapi` (or your framework of choice), and any adapters in your `requirements.txt`.

---

## Quick Start

```python
from haraka_runtime.orchestrator import Orchestrator
from haraka_runtime.core import Service
from fastapi import FastAPI


# 1. Define a Service
class MyService(Service):
    name = "my_service"

    async def startup(self):
        print("MyService starting up…")

    async def shutdown(self):
        print("MyService shutting down…")


# 2. Instantiate orchestrator
orch = Orchestrator()

# 3. Register your services
orch.use(MyService(), priority=5, dependencies=[])

# 4. Run (attach to your app)
app = FastAPI()  # or any DocsProvider


class Settings:
    port = 8000


await orch.run(Settings(), app)

# 5. Later, shut down gracefully
await orch.shutdown()
```

---

## Usage

1. **`use(service, priority=0, dependencies=[])`**  
   Register a `Service` instance with an integer priority and optional dependency names.

2. **`run(settings, app)`** → `None`  
   - Installs robust `SIGINT`/`SIGTERM` handlers  
   - Resolves startup order (topological + priority)  
   - Starts each service in order  
   - Schedules any background tasks  
   - Prints Swagger or docs URLs via `settings.port` and `app.docs_url`

3. **`wait_for_all_ready(timeout=30.0)`** → `None`  
   Block until all registered services call `mark_ready(name)` (or timeout).

4. **`shutdown()`** → `None`  
   - Cancels running tasks  
   - Stops services in reverse startup order  
   - Runs any registered shutdown tasks  
   - Transitions to `DESTROYED` state

5. **`mark_ready(name)`** → `None`  
   Signal that a particular service is “ready” (used by `wait_for_all_ready`).

---

## API Reference

| Method                                    | Signature                                                                        | Description                                              |
|-------------------------------------------|----------------------------------------------------------------------------------|----------------------------------------------------------|
| `use`                                     | `use(adapter: Adapter, priority: int = 0, dependencies: List[str] = []) -> None` | Register a service.                                       |
| `run`                                     | `async run(settings: Settings, app: DocsProvider) -> None`                       | Start all services and hook signals.                     |
| `wait_for_all_ready`                      | `async wait_for_all_ready(timeout: float = 30.0) -> None`                        | Await readiness of all services.                         |
| `shutdown`                                | `async shutdown() -> None`                                                       | Gracefully stop all services.                            |
| `mark_ready`                              | `mark_ready(name: str) -> None`                                                  | Mark a service as ready.                                 |

---

## Examples

### Basic Orchestration

```python
from haraka_runtime.orchestrator import Orchestrator
from haraka_runtime.core import Service


class DBService(Service):
    name = "db"

    async def startup(self): ...

    async def shutdown(self): ...


class APIService(Service):
    name = "api"

    async def startup(self): ...

    async def shutdown(self): ...


orch = Orchestrator()
orch.use(DBService(), priority=10)
orch.use(APIService(), priority=5, dependencies=["db"])

await orch.run(settings, app)  # starts db → api
await orch.shutdown()  # stops api → db
```

### Readiness Gating

```python
class CacheService(Service):
    name = "cache"
    async def startup(self):
        # simulate warm up…
        await asyncio.sleep(1)
        self.runtime.mark_ready(self.name)
    async def shutdown(self): …

orch = Orchestrator()
orch.use(CacheService())
# block until cache marks itself ready
await orch.wait_for_all_ready(timeout=5.0)
```

---

## Troubleshooting

- **Circular dependency**  
  You’ll see `RuntimeError: Circular dependency detected at X` if your graph has cycles.
- **Unknown dependency**  
  `RuntimeError: Unknown dependency 'foo' for service 'bar'` means you forgot to register `foo`.
- **Timeout waiting for services**  
  `TimeoutError` from `wait_for_all_ready` indicates one or more services never called `mark_ready()`.
- **Signal not triggering shutdown**  
  Ensure you use `run()` (which installs the robust `loop.add_signal_handler(...)` handlers).

---

## CI Integration

### GitHub Actions Example

Place this in `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10, 3.11, 3.12]

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install mypy pytest
      - name: Type-check with mypy
        run: mypy orchestrator/orchestrator.py --ignore-missing-imports
      - name: Run tests
        run: pytest --maxfail=1 --disable-warnings -q
```
