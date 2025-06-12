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

    def test_filter_prevents_publish(self):
        n1 = MagicMock(spec=NetworkInterface)
        bus = ContextBus([n1], filter_fn=lambda k, v: False)
        bus.publish("k", {"v": 1})
        n1.send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
