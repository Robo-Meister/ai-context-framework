from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


logger = logging.getLogger(__name__)


class FeedbackEventBus:
    """Simple publish/subscribe bus for goal feedback events."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._sync_warning_emitted = False

    def subscribe(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for future events."""
        self._subscribers.append(handler)
        logger.debug(
            "Registered feedback event handler",
            extra={"handler": getattr(handler, "__name__", repr(handler)), "subscriber_count": len(self._subscribers)},
        )

    def publish(self, event: Dict[str, Any]) -> None:
        """Send ``event`` to all subscribers."""
        if not self._sync_warning_emitted and len(self._subscribers) > 1:
            logger.warning(
                "FeedbackEventBus is operating synchronously; consider providing an async bus for high throughput",
                extra={"subscriber_count": len(self._subscribers)},
            )
            self._sync_warning_emitted = True
        self._dispatch_event(event, self._subscribers)

    @staticmethod
    def _dispatch_event(
        event: Dict[str, Any], handlers: Iterable[Callable[[Dict[str, Any]], None]]
    ) -> None:
        """Invoke ``handlers`` with ``event`` while protecting against failures."""

        for handler in list(handlers):
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Feedback event handler failed",
                    extra={
                        "handler": getattr(handler, "__name__", repr(handler)),
                        "event_keys": sorted(event.keys()),
                    },
                )


_STOP = object()


class AsyncFeedbackEventBus(FeedbackEventBus):
    """Publish/subscribe bus backed by :class:`asyncio.Queue`.

    Events published to this bus are enqueued and processed by background
    coroutines, allowing publishers to remain responsive even when handlers are
    slow. Consumers can be started explicitly via :meth:`add_background_consumer`.
    When an asyncio loop cannot be resolved the bus falls back to synchronous
    dispatch inherited from :class:`FeedbackEventBus`.
    """

    def __init__(
        self,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        queue_maxsize: int = 0,
        worker_count: int = 1,
    ) -> None:
        super().__init__()
        self._loop: Optional[asyncio.AbstractEventLoop] = loop
        self._queue: "asyncio.Queue[Dict[str, Any] | object]" = asyncio.Queue(
            maxsize=queue_maxsize
        )
        self._worker_count = max(1, worker_count)
        self._workers: List[asyncio.Task[None]] = []
        self._start_lock = threading.Lock()
        self._async_handlers: List[Tuple[Callable[[Dict[str, Any]], Any], bool]] = []
        self._workers_started = False
        self._async_warning_emitted = False

    def subscribe(self, handler: Callable[[Dict[str, Any]], Any]) -> None:  # type: ignore[override]
        super().subscribe(handler)
        is_async = asyncio.iscoroutinefunction(handler)
        if not is_async and hasattr(handler, "__call__"):
            is_async = asyncio.iscoroutinefunction(handler.__call__)  # type: ignore[arg-type]
        self._async_handlers.append((handler, is_async))

    def publish(self, event: Dict[str, Any]) -> None:  # type: ignore[override]
        loop = self._resolve_loop()
        if loop is None:
            if not self._async_warning_emitted:
                logger.warning(
                    "AsyncFeedbackEventBus could not locate a running event loop; falling back to synchronous dispatch",
                    extra={"subscriber_count": len(self._subscribers)},
                )
                self._async_warning_emitted = True
            super().publish(event)
            return
        self._ensure_workers(loop)

        def _put_nowait() -> None:
            try:
                self._queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.error(
                    "Async feedback event queue is full; dropping event",
                    extra={"queue_maxsize": self._queue.maxsize, "event_keys": sorted(event.keys())},
                )

        loop.call_soon_threadsafe(_put_nowait)

    def add_background_consumer(
        self,
        handler: Callable[[Dict[str, Any]], Any],
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> bool:
        """Register ``handler`` and ensure background workers are running.

        Returns ``True`` when an asyncio loop is active and the handler will be
        invoked asynchronously. When ``False`` is returned the handler remains
        registered but events will be processed synchronously by the base class.
        """

        self.subscribe(handler)
        resolved_loop = self._resolve_loop(loop)
        if resolved_loop is None:
            return False
        self._ensure_workers(resolved_loop)
        return True

    async def join(self) -> None:
        """Wait until all published events have been processed."""

        await self._queue.join()

    async def aclose(self) -> None:
        """Signal background workers to shut down and wait for completion."""

        if not self._workers:
            return
        for _ in range(len(self._workers)):
            await self._queue.put(_STOP)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._workers_started = False

    def close(self) -> None:
        """Synchronously shut down background workers if possible."""

        loop = self._resolve_loop()
        if loop and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self.aclose(), loop)
            future.result()
        else:
            self._workers.clear()
            self._workers_started = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_loop(
        self, explicit_loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> Optional[asyncio.AbstractEventLoop]:
        loop = explicit_loop or self._loop
        if loop is not None and loop.is_closed():
            loop = None
            self._loop = None
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
        if loop is None:
            try:
                candidate = asyncio.get_event_loop()
            except RuntimeError:
                candidate = None
            else:
                if candidate.is_running():
                    loop = candidate
        if loop is not None:
            self._loop = loop
        return loop

    def _ensure_workers(self, loop: asyncio.AbstractEventLoop) -> None:
        if self._workers_started:
            return
        with self._start_lock:
            if self._workers_started:
                return

            def _start() -> None:
                if self._workers_started:
                    return
                self._workers_started = True
                for index in range(self._worker_count):
                    task = asyncio.create_task(
                        self._worker(),
                        name=f"feedback-event-worker-{index}",
                    )
                    self._workers.append(task)

            loop.call_soon_threadsafe(_start)

    async def _worker(self) -> None:
        while True:
            event = await self._queue.get()
            if event is _STOP:
                self._queue.task_done()
                break
            try:
                await self._dispatch_async(event)
            finally:
                self._queue.task_done()

    async def _dispatch_async(self, event: Dict[str, Any]) -> None:
        for handler, is_async in list(self._async_handlers):
            try:
                if is_async:
                    await handler(event)
                else:
                    await asyncio.to_thread(handler, event)
            except Exception:
                logger.exception(
                    "Feedback event handler failed",
                    extra={
                        "handler": getattr(handler, "__name__", repr(handler)),
                        "event_keys": sorted(event.keys()),
                    },
                )
