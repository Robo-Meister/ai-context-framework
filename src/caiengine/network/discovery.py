"""Discovery service that keeps node membership in sync across the mesh."""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Callable, Dict, Optional

from .heartbeats import HeartbeatStore
from .node_registry import NodeRegistry


class DiscoveryError(Exception):
    """Raised when the discovery transport fails."""


class WebSocketDiscoveryClient:
    """Minimal interface used when pub/sub is unavailable."""

    def __init__(self, connect: Callable[[], Any]):
        self._connect = connect
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def start(self, on_message: Callable[[str], None]) -> None:
        if self._thread is not None:
            return

        def _run() -> None:
            self._running = True
            try:
                for payload in self._connect():
                    if not self._running:
                        break
                    on_message(payload)
            finally:
                self._running = False

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join()
            self._thread = None


class NodeDiscoveryService:
    """Maintain node membership via gossip messages and heartbeats."""

    def __init__(
        self,
        registry: NodeRegistry,
        heartbeat_store: HeartbeatStore,
        *,
        redis_client=None,
        gossip_channel: str = "mesh:gossip",
        websocket_client_factory: Optional[Callable[[], WebSocketDiscoveryClient]] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.registry = registry
        self.heartbeats = heartbeat_store
        self.redis = redis_client
        self.gossip_channel = gossip_channel
        self.websocket_client_factory = websocket_client_factory
        self.clock = clock

        self._listener_thread: Optional[threading.Thread] = None
        self._pubsub = None
        self._ws_client: Optional[WebSocketDiscoveryClient] = None
        self._running = False

    # -- lifecycle -----------------------------------------------------

    def start(self) -> None:
        if self._listener_thread is not None or self._running:
            return

        self._running = True
        if self.redis is None or not hasattr(self.redis, "pubsub"):
            self._start_websocket_fallback()
            return

        try:
            self._pubsub = self.redis.pubsub()
            self._pubsub.subscribe(self.gossip_channel)
        except Exception:
            self._start_websocket_fallback()
            return

        def _listen() -> None:
            try:
                for message in self._pubsub.listen():
                    if not self._running:
                        break
                    if not message or message.get("type") != "message":
                        continue
                    data = message.get("data")
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    self.process_gossip_message(data)
            finally:
                self._running = False

        self._listener_thread = threading.Thread(target=_listen, daemon=True)
        self._listener_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._listener_thread is not None:
            self._listener_thread.join()
            self._listener_thread = None
        if self._pubsub is not None:
            try:
                self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None
        if self._ws_client is not None:
            self._ws_client.stop()
            self._ws_client = None

    # -- gossip handling -----------------------------------------------

    def broadcast(self, payload: Dict[str, Any]) -> None:
        """Publish a gossip message to the configured channel."""

        if self.redis is None or not hasattr(self.redis, "publish"):
            return
        try:
            self.redis.publish(self.gossip_channel, json.dumps(payload))
        except Exception:
            pass

    def process_gossip_message(self, raw_message: Any) -> None:
        """Apply membership updates from a gossip payload."""

        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8")
        if isinstance(raw_message, str):
            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                return
        elif isinstance(raw_message, dict):
            payload = raw_message
        else:
            return

        robo_id = payload.get("robo_id")
        address = payload.get("address")
        if not robo_id or not address:
            return

        capabilities = payload.get("capabilities") or []
        drivers = payload.get("drivers") or []
        apps = payload.get("apps") or []
        meta = payload.get("meta") or {}

        self.registry.join(
            robo_id,
            address,
            capabilities=list(capabilities),
            drivers=list(drivers),
            apps=list(apps),
            meta=dict(meta),
        )
        heartbeat = payload.get("heartbeat")
        if heartbeat is not None:
            try:
                self.heartbeats.beat(robo_id, timestamp=float(heartbeat))
            except (TypeError, ValueError):
                pass

    # -- maintenance ---------------------------------------------------

    def prune_stale_nodes(self, *, max_age: float) -> None:
        """Remove nodes whose last heartbeat exceeds ``max_age`` seconds."""

        now = self.clock()
        for rid, last_seen in list(self.heartbeats.all().items()):
            if now - last_seen > max_age:
                self.registry.leave(rid)
                self.heartbeats.remove(rid)

    # -- helpers -------------------------------------------------------

    def _start_websocket_fallback(self) -> None:
        if self.websocket_client_factory is None:
            return

        self._ws_client = self.websocket_client_factory()
        self._ws_client.start(lambda message: self.process_gossip_message(message))

