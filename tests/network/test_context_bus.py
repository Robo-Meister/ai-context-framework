import unittest
from unittest.mock import MagicMock

from caiengine.network.context_bus import ContextBus
from caiengine.interfaces.network_interface import NetworkInterface


class TestContextBus(unittest.TestCase):
    def test_publish_sends_to_all_networks(self):
        n1 = MagicMock(spec=NetworkInterface)
        n2 = MagicMock(spec=NetworkInterface)
        bus = ContextBus([n1, n2])
        bus.publish("k", {"v": 1})
        n1.send.assert_called_once_with("all_nodes", {"key": "k", "value": {"v": 1}})
        n2.send.assert_called_once_with("all_nodes", {"key": "k", "value": {"v": 1}})
        n1.start_listening.assert_called()
        n2.start_listening.assert_called()

    def test_filter_prevents_publish(self):
        n1 = MagicMock(spec=NetworkInterface)
        bus = ContextBus([n1], filter_fn=lambda k, v: False)
        bus.publish("k", {"v": 1})
        n1.send.assert_not_called()

    def test_relays_received_message_to_other_networks(self):
        n1 = MagicMock(spec=NetworkInterface)
        n2 = MagicMock(spec=NetworkInterface)
        bus = ContextBus([n1, n2])
        # Capture callback registered for n1
        cb1 = n1.start_listening.call_args[0][0]
        cb1({"key": "a", "value": {"x": 1}})
        n2.send.assert_called_once_with("all_nodes", {"key": "a", "value": {"x": 1}})
        n1.send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
