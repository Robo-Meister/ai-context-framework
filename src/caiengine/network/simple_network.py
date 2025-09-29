"""Lightweight in-memory implementation of ``NetworkInterface`` for testing."""

from __future__ import annotations

import copy
import logging
import queue
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

from caiengine.interfaces.network_interface import NetworkInterface

logger = logging.getLogger(__name__)


class SimpleNetworkMock(NetworkInterface):
    """A small thread-safe network used in unit tests and local demos.

    The previous prototype relied on a plain list and offered no visibility
    into queued messages.  For production-like workloads we harden the mock by
    validating payloads, bounding the internal queue and collecting basic
    telemetry so tests can assert on network behaviour.
    """

    def __init__(self, *, max_queue: int = 1024):
        self.listening = False
        self._callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._thread: Optional[threading.Thread] = None
        self._queue: "queue.Queue[Tuple[str, Dict[str, Any], float]]" = queue.Queue(
            maxsize=max_queue
        )
        self._lock = threading.Lock()
        self._metrics: Dict[str, Any] = {
            "sent": 0,
            "broadcast": 0,
            "received": 0,
            "dropped": 0,
            "last_activity": None,
            "last_latency_ms": None,
            "last_error": None,
        }

    # ------------------------------------------------------------------ utils
    def _validate(self, recipient_id: str, message: Dict[str, Any]) -> None:
        if not isinstance(recipient_id, str) or not recipient_id:
            raise ValueError("recipient_id must be a non-empty string")
        if not isinstance(message, dict):
            raise ValueError("message must be a dictionary")

    def _enqueue(
        self, recipient_id: str, message: Dict[str, Any], *, is_broadcast: bool = False
    ) -> bool:
        self._validate(recipient_id, message)
        payload = (recipient_id, copy.deepcopy(message), time.time())
        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            with self._lock:
                self._metrics["dropped"] += 1
                self._metrics["last_activity"] = time.time()
                self._metrics["last_error"] = "queue_full"
            logger.warning("Mock network queue full; dropping message for %s", recipient_id)
            return False

        with self._lock:
            key = "broadcast" if is_broadcast else "sent"
            self._metrics[key] += 1
            self._metrics["last_activity"] = time.time()
            self._metrics["last_error"] = None
        logger.debug("Mock %s to %s: %s", "broadcast" if is_broadcast else "send", recipient_id, message)
        return True

    # ---------------------------------------------------------- NetworkInterface
    def send(self, recipient_id: str, message: Dict[str, Any]) -> bool:
        """Queue a message for ``recipient_id``.

        Returns ``True`` when the message has been queued and ``False`` when the
        queue is saturated and the message must be dropped.
        """

        return self._enqueue(recipient_id, message)

    def broadcast(self, message: Dict[str, Any]) -> bool:
        return self._enqueue("broadcast", message, is_broadcast=True)

    def receive(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        try:
            recipient, message, enqueued_at = self._queue.get_nowait()
        except queue.Empty:
            return None

        latency_ms = max((time.time() - enqueued_at) * 1000.0, 0.0)
        with self._lock:
            self._metrics["received"] += 1
            self._metrics["last_activity"] = time.time()
            self._metrics["last_latency_ms"] = latency_ms
        return recipient, message

    def start_listening(self, on_message_callback: Callable[[Dict[str, Any]], None]):
        """Process queued messages in a background thread."""

        self._callback = on_message_callback
        if not self.listening:
            self.listening = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def _loop(self) -> None:
        while self.listening:
            msg = self.receive()
            if msg and self._callback:
                _recipient, message = msg
                try:
                    self._callback(message)
                except Exception:  # pragma: no cover - defensive
                    logger.exception("Mock network callback failed")
            else:
                time.sleep(0.05)

    def stop_listening(self) -> None:
        self.listening = False
        if self._thread:
            self._thread.join()
            self._thread = None

    # ---------------------------------------------------------------- telemetry
    def stats(self) -> Dict[str, Any]:
        """Return a snapshot of internal telemetry metrics."""

        with self._lock:
            metrics = dict(self._metrics)
            metrics["queue_size"] = self._queue.qsize()
            metrics["listening"] = self.listening
        return metrics
