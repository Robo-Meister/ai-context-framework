import argparse
import json
from http.server import HTTPServer
import threading

from caiengine.providers.http_context_provider import HTTPContextProvider
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.core.goal_strategies import SimpleGoalFeedbackStrategy


class CAIService:
    """Combined HTTP service exposing context and feedback endpoints."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.provider = HTTPContextProvider(host=host, port=port)
        self.feedback_loop = GoalDrivenFeedbackLoop(SimpleGoalFeedbackStrategy())
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

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
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    super().do_POST()

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
    args = parser.parse_args(argv)

    service = CAIService(host=args.host, port=args.port)
    service.start()
    try:
        if service._thread:
            service._thread.join()
    except KeyboardInterrupt:
        service.stop()


if __name__ == "__main__":
    main()
