"""Node agent implementation responsible for registration and task handling."""

from __future__ import annotations

import threading
import time
from typing import Callable, Dict, Iterable, Optional

from .heartbeats import HeartbeatStore
from .node_registry import NodeRegistry
from .node_tasks import NodeTask, NodeTaskQueue
from .roboid import RoboId


TaskHandler = Callable[[NodeTask], None]


class NodeAgent:
    """Agent that represents a node inside the distributed control plane."""

    def __init__(
        self,
        robo_id: RoboId | str,
        registry: NodeRegistry,
        heartbeat_store: HeartbeatStore,
        task_queue: NodeTaskQueue,
        *,
        heartbeat_interval: float = 5.0,
        heartbeat_grace: float = 15.0,
        task_poll_interval: float = 0.25,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.robo_id = str(robo_id)
        self.registry = registry
        self.heartbeats = heartbeat_store
        self.task_queue = task_queue
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_grace = heartbeat_grace
        self.task_poll_interval = task_poll_interval
        self.clock = clock

        self._capabilities: set[str] = set()
        self._drivers: set[str] = set()
        self._apps: set[str] = set()
        self._meta: Dict[str, object] = {}
        self._address: Optional[str] = None

        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._task_thread: Optional[threading.Thread] = None
        self._task_handler: Optional[TaskHandler] = None

    # -- lifecycle -----------------------------------------------------

    def start(
        self,
        address: str,
        *,
        capabilities: Optional[Iterable[str]] = None,
        drivers: Optional[Iterable[str]] = None,
        apps: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, object]] = None,
        task_handler: Optional[TaskHandler] = None,
    ) -> None:
        """Register the node and begin heartbeat/task processing."""

        self._capabilities = set(capabilities or [])
        self._drivers = set(drivers or [])
        self._apps = set(apps or [])
        self._meta = dict(metadata or {})
        self._address = address

        self.registry.join(
            self.robo_id,
            address,
            capabilities=sorted(self._capabilities),
            drivers=sorted(self._drivers),
            apps=sorted(self._apps),
            meta=self._meta,
        )

        self._running = True
        self._task_handler = task_handler
        self._start_heartbeat_loop()
        if task_handler is not None:
            self._start_task_loop()

    def stop(self, *, deregister: bool = False) -> None:
        """Stop background loops and optionally remove the node from the registry."""

        self._running = False
        if self._heartbeat_thread is not None:
            self._heartbeat_thread.join()
            self._heartbeat_thread = None
        if self._task_thread is not None:
            self._task_thread.join()
            self._task_thread = None
        if deregister:
            self.registry.leave(self.robo_id)
        self.heartbeats.remove(self.robo_id)
        self._address = None

    # -- registration updates -----------------------------------------

    def update_capabilities(self, capabilities: Iterable[str]) -> None:
        self._capabilities = set(capabilities)
        self.registry.update(self.robo_id, capabilities=sorted(self._capabilities))

    def update_metadata(self, **metadata: object) -> None:
        self._meta.update(metadata)
        self.registry.update(self.robo_id, meta=self._meta)

    def register_driver(self, *drivers: str) -> None:
        self._drivers.update(drivers)
        self.registry.update(self.robo_id, drivers=sorted(self._drivers))

    def register_app(self, *apps: str) -> None:
        self._apps.update(apps)
        self.registry.update(self.robo_id, apps=sorted(self._apps))

    # -- heartbeat management -----------------------------------------

    def _start_heartbeat_loop(self) -> None:
        if self._heartbeat_thread is not None:
            return

        def _loop() -> None:
            next_due = self.clock()
            while self._running:
                now = self.clock()
                if now >= next_due:
                    self.heartbeats.beat(self.robo_id, timestamp=now)
                    next_due = now + self.heartbeat_interval
                time.sleep(min(self.heartbeat_interval, 0.25))

        self._heartbeat_thread = threading.Thread(target=_loop, daemon=True)
        self._heartbeat_thread.start()

    # -- task processing -----------------------------------------------

    def _start_task_loop(self) -> None:
        if self._task_thread is not None or self._task_handler is None:
            return

        def _loop() -> None:
            while self._running:
                task = self.task_queue.dequeue(self.robo_id, block=False)
                if task is None:
                    time.sleep(self.task_poll_interval)
                    continue
                try:
                    self._task_handler(task)
                except Exception:
                    # Intentionally swallow exceptions so the loop keeps running.
                    pass

        self._task_thread = threading.Thread(target=_loop, daemon=True)
        self._task_thread.start()

    def submit_task(self, target: RoboId | str, payload: Dict[str, object]) -> NodeTask:
        """Enqueue a task for another node in the mesh."""

        return self.task_queue.enqueue(target, dict(payload))

    # -- inspection ----------------------------------------------------

    def last_heartbeat_age(self) -> Optional[float]:
        """Return the seconds since the last heartbeat was recorded."""

        last = self.heartbeats.last_seen(self.robo_id)
        if last is None:
            return None
        return max(0.0, self.clock() - last)

    def snapshot(self) -> Dict[str, object]:
        """Return the current state advertised for gossip broadcasts."""

        return {
            "robo_id": self.robo_id,
            "address": self._address,
            "capabilities": sorted(self._capabilities),
            "drivers": sorted(self._drivers),
            "apps": sorted(self._apps),
            "meta": dict(self._meta),
            "heartbeat": self.heartbeats.last_seen(self.robo_id),
        }

