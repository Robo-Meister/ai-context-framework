import time
from network.network_manager import NetworkManager
from network.simple_network import SimpleNetworkMock


def test_network_manager_invokes_callback():
    net = SimpleNetworkMock()
    mgr = NetworkManager(net)
    received = []

    mgr.start_listening(lambda msg: received.append(msg))
    net.send("node1", {"ping": "pong"})
    time.sleep(0.1)
    mgr.stop_listening()

    assert {"ping": "pong"} in received


def test_simple_network_mock_start_listening():
    net = SimpleNetworkMock()
    received = []
    net.start_listening(lambda msg: received.append(msg))
    net.send("node1", {"foo": "bar"})
    time.sleep(0.1)
    net.stop_listening()

    assert {"foo": "bar"} in received

