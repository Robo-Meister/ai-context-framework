import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
from importlib import import_module
from typing import Any, Dict, Optional
import threading
from urllib.parse import urlparse, parse_qs

from caiengine.objects.context_query import ContextQuery
from caiengine.objects.context_data import ContextData
from caiengine.providers.memory_context_provider import MemoryContextProvider


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
        self.backend = self._prepare_backend(backend)
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.debug(
            "HTTP context provider initialised",
            extra={"host": self.host, "port": self.port, "backend": self.backend.__class__.__name__},
        )

    def _prepare_backend(self, backend: Optional[object]) -> object:
        if backend is None:
            return MemoryContextProvider()

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

    # ---- HTTP Handlers -------------------------------------------------
    def _make_handler(self):
        provider = self

        class Handler(BaseHTTPRequestHandler):
            def _respond(self, code: int, data: dict | list):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                def convert(o):
                    if isinstance(o, datetime):
                        return o.isoformat()
                    raise TypeError
                self.wfile.write(json.dumps(data, default=convert).encode())

            def do_POST(self):
                if self.path != "/context":
                    provider.logger.warning(
                        "Received request for unknown path", extra={"path": self.path}
                    )
                    self._respond(404, {"error": "not found"})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    provider.logger.warning(
                        "Rejected context ingestion due to invalid JSON",
                        extra={"remote_ip": self.client_address[0]},
                    )
                    self._respond(400, {"error": "invalid json"})
                    return

                ts_val = payload.get("timestamp")
                timestamp = datetime.fromisoformat(ts_val) if ts_val else None
                context_id = provider.backend.ingest_context(
                    payload.get("payload", {}),
                    timestamp=timestamp,
                    metadata=payload.get("metadata"),
                    source_id=payload.get("source_id", "http"),
                    confidence=float(payload.get("confidence", 1.0)),
                )
                provider.logger.info(
                    "Accepted context ingestion via HTTP",
                    extra={"context_id": context_id, "remote_ip": self.client_address[0]},
                )
                self._respond(200, {"id": context_id})

            def do_GET(self):
                if not self.path.startswith("/context"):
                    provider.logger.warning(
                        "Received request for unknown path", extra={"path": self.path}
                    )
                    self._respond(404, {"error": "not found"})
                    return
                qs = parse_qs(urlparse(self.path).query)
                start_s = qs.get("start", [None])[0]
                end_s = qs.get("end", [None])[0]
                start = datetime.fromisoformat(start_s) if start_s else datetime.min
                end = datetime.fromisoformat(end_s) if end_s else datetime.utcnow()
                query = ContextQuery(roles=[], time_range=(start, end), scope="", data_type="")
                data = provider.backend.get_context(query)
                provider.logger.debug(
                    "Served context fetch", extra={"count": len(data), "remote_ip": self.client_address[0]}
                )
                self._respond(200, data)

            def log_message(self, format, *args):  # silence default logging
                return

        return Handler

    # ---- Server Lifecycle ----------------------------------------------
    def start(self):
        if self._server:
            self.logger.debug("HTTP server already running; start ignored")
            return
        handler = self._make_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.logger.info("HTTP context provider started", extra={"host": self.host, "port": self.port})

    def stop(self):
        if self._server:
            self._server.shutdown()
            if self._thread:
                self._thread.join()
            self._server.server_close()
            self._server = None
            self._thread = None
            self.logger.info("HTTP context provider stopped")

    # ---- Direct API wrappers ------------------------------------------
    def ingest_context(self, *args, **kwargs):
        return self.backend.ingest_context(*args, **kwargs)

    def fetch_context(self, query_params: ContextQuery):
        return self.backend.fetch_context(query_params)

    def get_context(self, query: ContextQuery):
        return self.backend.get_context(query)

    def subscribe_context(self, callback):
        return self.backend.subscribe_context(callback)
