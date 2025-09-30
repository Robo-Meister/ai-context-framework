import argparse
import json
from http.server import HTTPServer
import threading

from caiengine.providers.http_context_provider import HTTPContextProvider
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import SimpleGoalFeedbackStrategy
from caiengine.common.token_usage import TokenCounter


class CAIService:
    """Combined HTTP service exposing context and feedback endpoints."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, backend: object | None = None):
        self.host = host
        self.port = port
        self.provider = HTTPContextProvider(host=host, port=port, backend=backend)
        self.feedback_loop = GoalDrivenFeedbackLoop(SimpleGoalFeedbackStrategy())
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None
        self.token_counter = TokenCounter()

    def _make_handler(self):
        base_handler = self.provider._make_handler()
        service = self

        class Handler(base_handler):
            def do_POST(self):
                if self.path == "/suggest":
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length)
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError:
                        self.send_response(400)
                        self.end_headers()
                        return

                    history = payload.get("history", [])
                    current_actions = payload.get("current_actions", [])
                    goal_state = payload.get("goal_state")
                    if goal_state is not None:
                        service.feedback_loop.set_goal_state(goal_state)
                    result = service.feedback_loop.suggest(history, current_actions)
                    items = result if isinstance(result, list) else [result]
                    for item in items:
                        usage = item.get("usage") if isinstance(item, dict) else None
                        if usage:
                            service.token_counter.add(usage)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    super().do_POST()

            def do_GET(self):
                if self.path == "/usage":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(service.token_counter.as_dict()).encode()
                    )
                else:
                    super().do_GET()

        return Handler

    def start(self):
        if self._server:
            return
        handler = self._make_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        if self._server:
            self._server.shutdown()
            if self._thread:
                self._thread.join()
            self._server.server_close()
            self._server = None
            self._thread = None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Start CAIEngine service")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    parser.add_argument("--backend", default=None, help="Backend provider class path")
    parser.add_argument(
        "--backend-options",
        default=None,
        help="JSON encoded keyword arguments for the backend provider",
    )
    args = parser.parse_args(argv)

    backend_spec = None
    if args.backend:
        options = json.loads(args.backend_options) if args.backend_options else {}
        backend_spec = {"path": args.backend, "options": options}

    service = CAIService(host=args.host, port=args.port, backend=backend_spec)
    service.start()
    try:
        if service._thread:
            service._thread.join()
    except KeyboardInterrupt:
        service.stop()


if __name__ == "__main__":
    main()
