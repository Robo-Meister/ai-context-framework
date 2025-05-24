from interfaces.network_interface import NetworkInterface


class SimpleNetwork(NetworkInterface):
    """
    Simple mock that simulates network communication via an internal queue.
    Useful for testing distributed context sync.
    """
    def __init__(self):
        self.queue = []

    def send(self, destination: str, message: dict) -> bool:
        print(f"[MockNetwork] Sending message to {destination}: {message}")
        self.queue.append((destination, message))
        return True

    def receive(self) -> dict:
        if self.queue:
            dest, msg = self.queue.pop(0)
            print(f"[MockNetwork] Received message for {dest}: {msg}")
            return {"destination": dest, "message": msg}
        return None