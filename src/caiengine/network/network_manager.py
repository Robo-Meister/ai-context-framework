"""High level networking utilities for Contextual AI nodes.

This module exposes :class:`NetworkManager`, a wrapper around a raw
:class:`~caiengine.interfaces.network_interface.NetworkInterface` that provides
quality-of-life helpers for managing mesh nodes, dispatching work and creating
node agents.  The goal is to offer a single entry point that coordinates both
transport and control-plane concerns while remaining backwards compatible with
existing code that only relied on the basic networking primitives.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Iterable, Optional, Union

from caiengine.interfaces.network_interface import NetworkInterface

from .capability_registry import CapabilityRegistry
from .dispatcher import DispatchOutcome, MeshDispatcher
from .discovery import NodeDiscoveryService
from .heartbeats import HeartbeatStore
from .node_agent import NodeAgent, TaskHandler
from .node_manager import NodeInfo, NodeManager
from .node_registry import NodeRegistry
from .node_tasks import NodeTaskQueue
from .roboid import RoboId


class NetworkManager(NetworkInterface):
    """High-level manager wrapping a :class:`NetworkInterface` implementation.

    Besides the raw send/receive helpers the manager lazily exposes
    ``NodeManager``/``CapabilityRegistry`` and ``MeshDispatcher`` instances when
    a :class:`NodeRegistry` (or already instantiated manager) is provided.  This
    keeps the API compact while enabling advanced orchestration features.
    """

    def __init__(
        self,
        network_interface: NetworkInterface,
        *,
        registry: Optional[NodeRegistry] = None,
        heartbeat_store: Optional[HeartbeatStore] = None,
        task_queue: Optional[NodeTaskQueue] = None,
        discovery: Optional[NodeDiscoveryService] = None,
        node_registry: Optional[NodeRegistry] = None,
        node_manager: Optional[NodeManager] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        mesh_dispatcher: Optional[MeshDispatcher] = None,
    ) -> None:
        self.network_interface = network_interface
        self.listening = False
        self.on_message_callback = None
        self._listen_thread: Optional[threading.Thread] = None

        # Backwards compatibility: ``registry`` historically exposed the
        # control-plane registry.  Prefer ``node_registry`` when supplied.
        primary_registry = node_registry or registry
        self.registry = primary_registry
        self.heartbeats = heartbeat_store
        self.task_queue = task_queue
        self.discovery = discovery

        self._node_registry = primary_registry
        self._node_manager = node_manager
        self._capability_registry = capability_registry
        self._mesh_dispatcher = mesh_dispatcher

    # ------------------------------------------------------------------
    # Transport level helpers
    # ------------------------------------------------------------------
    def send(self, recipient_id: str, message: dict) -> None:
        self.network_interface.send(recipient_id, message)

    def broadcast(self, message: dict) -> None:
        self.network_interface.broadcast(message)

    def receive(self):
        """Return the next message from the underlying network if available."""

        return self.network_interface.receive()

    def _listen_loop(self) -> None:
        """Background thread fetching messages and invoking the callback."""

        while self.listening:
            msg = self.receive()
            if msg:
                _recipient, message = msg
                if self.on_message_callback:
                    self.on_message_callback(message)
            else:
                time.sleep(0.02)  # avoid busy waiting

    def start_listening(self, on_message_callback) -> None:
        """Begin asynchronously listening for incoming messages."""

        self.on_message_callback = on_message_callback
        if not self.listening:
            self.listening = True
            self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._listen_thread.start()

    def stop_listening(self) -> None:
        """Stop the background listening thread."""

        self.listening = False
        if self._listen_thread:
            self._listen_thread.join()
            self._listen_thread = None

    # ------------------------------------------------------------------
    # Control plane helpers
    # ------------------------------------------------------------------
    def create_node_agent(
        self,
        robo_id: Union[str, RoboId],
        address: str,
        *,
        capabilities: Optional[Iterable[str]] = None,
        drivers: Optional[Iterable[str]] = None,
        apps: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        heartbeat_interval: float = 5.0,
        task_handler: Optional[TaskHandler] = None,
    ) -> NodeAgent:
        """Instantiate and start a :class:`NodeAgent` for the given node."""

        if not (self.registry and self.heartbeats and self.task_queue):
            raise RuntimeError("Control-plane components not configured for NetworkManager")

        manager = self._ensure_node_manager()
        manager.register(
            robo_id,
            address,
            capabilities=list(capabilities or []),
            drivers=list(drivers or []),
            apps=list(apps or []),
            metadata=dict(metadata or {}),
        )

        agent = NodeAgent(
            robo_id,
            self.registry,
            self.heartbeats,
            self.task_queue,
            heartbeat_interval=heartbeat_interval,
        )
        agent.start(
            address,
            capabilities=capabilities,
            drivers=drivers,
            apps=apps,
            metadata=metadata,
            task_handler=task_handler,
        )
        if self.discovery is not None:
            self.discovery.broadcast(agent.snapshot())
        return agent

    # ------------------------------------------------------------------
    # Mesh / node management helpers
    # ------------------------------------------------------------------
    def attach_node_registry(self, registry: NodeRegistry) -> None:
        """Attach a :class:`NodeRegistry` and reset cached helpers.

        The ``NetworkManager`` caches helper instances for efficiency.  When the
        registry changes we clear the caches to ensure fresh state is loaded.
        """

        self.registry = registry
        self._node_registry = registry
        self._node_manager = None
        self._capability_registry = None
        self._mesh_dispatcher = None

    # -- lazy properties -------------------------------------------------
    def _require_node_registry(self) -> NodeRegistry:
        registry = self._node_registry
        if registry is None:
            raise RuntimeError(
                "Node registry not configured. Attach a NodeRegistry before using mesh helpers.",
            )
        return registry

    def _ensure_node_manager(self) -> NodeManager:
        if self._node_manager is not None:
            return self._node_manager
        registry = self._require_node_registry()
        self._node_manager = NodeManager(registry)
        return self._node_manager

    def _ensure_capability_registry(self) -> CapabilityRegistry:
        if self._capability_registry is not None:
            return self._capability_registry
        node_manager = self._ensure_node_manager()
        self._capability_registry = CapabilityRegistry(node_manager)
        return self._capability_registry

    def _ensure_mesh_dispatcher(self) -> MeshDispatcher:
        if self._mesh_dispatcher is not None:
            return self._mesh_dispatcher
        capability_registry = self._ensure_capability_registry()
        self._mesh_dispatcher = MeshDispatcher(capability_registry, self)
        return self._mesh_dispatcher

    @property
    def node_manager(self) -> NodeManager:
        """Return the lazily created :class:`NodeManager`."""

        return self._ensure_node_manager()

    @property
    def capability_registry(self) -> CapabilityRegistry:
        """Return the lazily created :class:`CapabilityRegistry`."""

        return self._ensure_capability_registry()

    @property
    def mesh_dispatcher(self) -> MeshDispatcher:
        """Return the lazily created :class:`MeshDispatcher`."""

        return self._ensure_mesh_dispatcher()

    # -- public mesh helpers --------------------------------------------
    def register_node(
        self,
        robo_id: Union[str, RoboId],
        address: str,
        *,
        capabilities: Optional[Iterable[str]] = None,
        drivers: Optional[Iterable[str]] = None,
        apps: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[NodeInfo]:
        """Register a node and return its metadata."""

        manager = self._ensure_node_manager()
        manager.register(
            robo_id,
            address,
            capabilities=list(capabilities or []),
            drivers=list(drivers or []),
            apps=list(apps or []),
            metadata=dict(metadata or {}),
        )
        return manager.get(robo_id)

    def unregister_node(self, robo_id: Union[str, RoboId]) -> None:
        """Remove ``robo_id`` from the node registry if configured."""

        manager = self._ensure_node_manager()
        manager.unregister(robo_id)

    def update_node(
        self,
        robo_id: Union[str, RoboId],
        *,
        address: Optional[str] = None,
        capabilities: Optional[Iterable[str]] = None,
        drivers: Optional[Iterable[str]] = None,
        apps: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[NodeInfo]:
        """Update metadata for ``robo_id`` and return the refreshed info."""

        manager = self._ensure_node_manager()
        manager.update_inventory(
            robo_id,
            address=address,
            capabilities=list(capabilities) if capabilities is not None else None,
            drivers=list(drivers) if drivers is not None else None,
            apps=list(apps) if apps is not None else None,
            metadata=dict(metadata) if metadata is not None else None,
        )
        return manager.get(robo_id)

    def find_nodes(
        self,
        *,
        capabilities: Optional[Iterable[str]] = None,
        drivers: Optional[Iterable[str]] = None,
        apps: Optional[Iterable[str]] = None,
    ) -> Dict[str, NodeInfo]:
        """Return nodes that satisfy the requested inventory filters."""

        manager = self._ensure_node_manager()
        return manager.find_nodes(
            capabilities=list(capabilities or []),
            drivers=list(drivers or []),
            apps=list(apps or []),
        )

    def dispatch_to_mesh(
        self,
        pack: Dict[str, Any],
        *,
        origin: Optional[str] = None,
        requirements: Optional[Dict[str, Iterable[str]]] = None,
    ) -> DispatchOutcome:
        """Dispatch a command pack using the mesh dispatcher.

        This is a thin wrapper around :meth:`MeshDispatcher.dispatch` that keeps
        ``NetworkManager`` as the central orchestration entry-point.
        """

        dispatcher = self._ensure_mesh_dispatcher()
        return dispatcher.dispatch(pack, origin=origin, requirements=requirements)
