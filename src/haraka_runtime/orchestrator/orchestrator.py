import asyncio
import signal
import socket
from enum import Enum, auto
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Set, Protocol

from haraka.utils import Logger

from src.haraka_runtime.core.interfaces import Adapter


class DocsProvider(Protocol):
    docs_url: str

class Settings(Protocol):
    port: int

class LifecycleState(Enum):
    UNINITIALIZED = auto()
    STARTED = auto()
    DESTROYED = auto()

class Orchestrator:
    def __init__(self, variant: str = "PyFast"):
        self.variant = variant
        self.logger = Logger(self.variant).start_logger()
        self.state = LifecycleState.UNINITIALIZED

        self._registry: Dict[str, Tuple[Adapter, int, List[str]]] = {}
        self._adapter_events: Dict[str, asyncio.Event] = {}

        self.startup_tasks: List[Callable[[], Awaitable]] = []
        self.shutdown_tasks: List[Callable[[], Awaitable]] = []
        self._running_tasks: List[asyncio.Task] = []

        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def use(
        self,
        adapter: Adapter,
        priority: int = 0,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        name = adapter.name
        deps = dependencies or []
        if name in self._registry:
            self.logger.warn(f"⚠️ Adapter '{name}' already registered")
            return
        self._registry[name] = (adapter, priority, deps)
        self._adapter_events[name] = asyncio.Event()
        # set runtime attribute dynamically
        setattr(adapter, 'runtime', self)
        self.logger.debug(f"🛎️ Registered adapter: {name} (priority={priority}, dependencies={deps})")

    def mark_ready(self, name: str):
        event = self._adapter_events.get(name)
        if event and not event.is_set():
            event.set()
            self.logger.info(f"✅ Adapter '{name}' is ready.")
        elif event:
            self.logger.debug(f"🔁 Adapter '{name}' was already marked ready.")
        else:
            self.logger.warn(f"⚠️ Tried to mark unknown adapter '{name}' as ready")

    async def wait_for_all_ready(self, timeout: float = 30.0):
        try:
            await asyncio.wait_for(
                asyncio.gather(*(evt.wait() for evt in self._adapter_events.values())),
                timeout=timeout
            )
            self.logger.info("✅ All declared adapters are up and running!")
        except asyncio.TimeoutError:
            unready = [n for n, e in self._adapter_events.items() if not e.is_set()]
            self.logger.error("❌ Timed out waiting for adapters", extra={"unready_adapters": unready})
            raise

    def _resolve_start_order(self) -> List[Adapter]:
        graph: Dict[str, Set[str]] = {name: set(deps) for name, (_, _, deps) in self._registry.items()}
        order: List[str] = []
        temp = set()

        def visit(node: str):
            if node in temp:
                raise RuntimeError(f"Circular dependency detected at {node}")
            if node not in order:
                temp.add(node)
                for dep in graph.get(node, []):
                    if dep not in graph:
                        raise RuntimeError(f"Unknown dependency '{dep}' for adapter '{node}'")
                    visit(dep)
                temp.remove(node)
                order.append(node)

        for name in graph:
            visit(name)

        resolved = [(self._registry[n][1], n) for n in order]
        resolved.sort(key=lambda x: -x[0])
        return [self._registry[name][0] for _, name in resolved]

    def _on_signal(self, signum: int) -> None:
        self.logger.info(f"🔔 Received signal {signal.Signals(signum).name}, initiating shutdown...")
        asyncio.create_task(self.shutdown())

    async def run(self, settings: Settings, app: DocsProvider) -> None:
        if self.state != LifecycleState.UNINITIALIZED:
            self.logger.warn(f"🟡 Already started or shut down: {self.state.name}")
            return

        # Install robust signal handlers on the running loop
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._on_signal, sig)

        start_order = self._resolve_start_order()
        for svc in start_order:
            try:
                await svc.startup()
                self.logger.info(f"🚀 Started {svc.name}")
            except Exception as e:
                self.logger.error(f"❌ Failed to start {svc.name}", extra={"error": str(e)})
                raise

        for task_fn in self.startup_tasks:
            task = asyncio.create_task(self._wrap_task(task_fn))
            self._running_tasks.append(task)

        self._print_docs_url(settings, app)
        self.state = LifecycleState.STARTED

    async def shutdown(self):
        if self.state != LifecycleState.STARTED:
            self.logger.warn("🟡 Not running or already destroyed")
            return

        self.logger.info("🛑 Application is shutting down!")

        for task in self._running_tasks:
            task.cancel()
        await asyncio.gather(*self._running_tasks, return_exceptions=True)

        for svc in reversed(self._resolve_start_order()):
            try:
                await svc.shutdown()
                self.logger.info(f"🛑 Stopped {svc.name}")
            except Exception as e:
                self.logger.error(f"❌ Shutdown failed for {svc.name}", extra={"error": str(e)})

        for task_fn in self.shutdown_tasks:
            try:
                await task_fn()
            except Exception as e:
                self.logger.error("❌ Shutdown task failed:", extra={"error": str(e)})

        self.state = LifecycleState.DESTROYED

    def _handle_signal(self, signum, _frame):
        self.logger.info(f"🔔 Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.shutdown())

    async def _wrap_task(self, coro_fn: Callable[[], Awaitable]):
        try:
            await coro_fn()
        except asyncio.CancelledError:
            self.logger.info(f"🛑 Task {coro_fn.__name__} cancelled.")
        except Exception:
            self.logger.error(f"❌ Task {coro_fn.__name__} failed:")
            raise

    def _print_docs_url(self, settings: Settings, app: DocsProvider):
        try:
            port = settings.port
            docs_path = app.docs_url or "/docs"
            local = f"http://localhost:{port}{docs_path}"
            host = socket.gethostbyname(socket.gethostname())
            net = f"http://{host}:{port}{docs_path}"
            self.logger.info(f"✅ Swagger UI available at: {local}")
            self.logger.info(f"🌐 Network Swagger UI available at: {net}")
        except Exception as e:
            self.logger.warn(f"⚠️ Failed to determine docs URL: {e}")
