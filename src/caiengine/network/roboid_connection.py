import json
import socket
import threading
import time
from typing import Optional

from caiengine.interfaces.network_interface import NetworkInterface


class RoboIdConnection(NetworkInterface):
    """Simple TCP connection that sends newline-delimited JSON messages."""

    def __init__(self, sock: socket.socket):
        self.socket = sock
        self.socket.settimeout(0.1)
        self._buffer = b""
        self._lock = threading.Lock()
        self.listening = False
        self._callback = None
        self._thread: Optional[threading.Thread] = None

    def send(self, recipient_id: str, message: dict):
        payload = json.dumps({"recipient": recipient_id, "message": message})
        data = payload.encode("utf-8") + b"\n"
        with self._lock:
            self.socket.sendall(data)

    def broadcast(self, message: dict):
        self.send("broadcast", message)

    def receive(self):
        while True:
            try:
                chunk = self.socket.recv(4096)
            except socket.timeout:
                return None
            if not chunk:
                return None
            self._buffer += chunk
            if b"\n" in self._buffer:
                line, self._buffer = self._buffer.split(b"\n", 1)
                return json.loads(line.decode("utf-8"))

    def start_listening(self, on_message_callback):
        self._callback = on_message_callback
        if self.listening:
            return
        self.listening = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self.listening:
            msg = self.receive()
            if msg and self._callback:
                self._callback(msg)
            else:
                time.sleep(0.05)

    def stop_listening(self):
        self.listening = False
        if self._thread:
            self._thread.join()
            self._thread = None

