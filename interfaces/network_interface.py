class NetworkInterface:
    """
    Abstract network interface to send/receive context data and messages
    between distributed components.
    """
    def send(self, destination: str, message: dict) -> bool:
        """
        Send a message to the given destination node.
        """
        raise NotImplementedError

    def receive(self) -> dict:
        """
        Blocking or async receive to get incoming messages.
        """
        raise NotImplementedError
