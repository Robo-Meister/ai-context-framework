import logging
import threading
from importlib import import_module
from typing import Any, Dict, Optional

from caiengine.objects.context_query import ContextQuery
from caiengine.providers.memory_context_provider import MemoryContextProvider
from caiengine.providers.http_service import create_http_service_app


class HTTPContextProvider:
    """Expose a simple REST API for context ingestion and retrieval."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        backend: Optional[object] = None,
    ):
        self.host = host
        self.port = port
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.backend = self._prepare_backend(backend)
        self._app: Any | None = None
        self._server: Any | None = None
        self._thread: Optional[threading.Thread] = None

    def _prepare_backend(self, backend: Optional[object]) -> object:
        if backend is None:
            provider = MemoryContextProvider()
            self.logger.warning(
                "HTTPContextProvider defaulting to MemoryContextProvider backend",
                extra={"backend": "memory"},
            )
            return provider

        if isinstance(backend, str):
            return self._load_backend_from_path(backend, {})

        if isinstance(backend, dict):
            path = backend.get("path")
            if not path:
                raise ValueError("Backend configuration must include 'path'")
            options = backend.get("options", {})
            if not isinstance(options, dict):
                raise TypeError("Backend 'options' must be a mapping of keyword arguments")
            return self._load_backend_from_path(path, options)

        if hasattr(backend, "ingest_context") and hasattr(backend, "get_context"):
            return backend

        raise TypeError("Unsupported backend specification for HTTPContextProvider")

    @staticmethod
    def _load_backend_from_path(path: str, options: Dict[str, Any]) -> object:
        module_name, class_name = path.rsplit(".", 1)
        module = import_module(module_name)
        backend_cls = getattr(module, class_name)
        return backend_cls(**options)

    def _create_app(self):
        return create_http_service_app(
            provider=self,
            logger=self.logger,
            include_goal_routes=False,
        )

    @property
    def app(self):
        if self._app is None:
            self._app = self._create_app()
        return self._app

    # ---- Server Lifecycle ----------------------------------------------
    def _create_server(self):
        import uvicorn

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_config=None,
        )
        return uvicorn.Server(config)

    def serve(self):
        """Run the FastAPI app in the current thread."""

        server = self._create_server()
        server.run()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._server = self._create_server()
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self.logger.info(
            "Starting HTTP context provider",
            extra={"host": self.host, "port": self.port},
        )
        self._thread.start()

    def stop(self):
        if self._server is None:
            return
        self._server.should_exit = True
        if self._thread:
            self._thread.join()
        self.logger.info(
            "Stopped HTTP context provider",
            extra={"host": self.host, "port": self.port},
        )
        self._server = None
        self._thread = None

    # ---- Direct API wrappers ------------------------------------------
    def ingest_context(self, *args, **kwargs):
        return self.backend.ingest_context(*args, **kwargs)

    def fetch_context(self, query_params: ContextQuery):
        return self.backend.fetch_context(query_params)

    def get_context(self, query: ContextQuery):
        return self.backend.get_context(query)

    def subscribe_context(self, callback):
        return self.backend.subscribe_context(callback)
