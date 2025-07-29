import socket
import time
import unittest
import importlib.util
from pathlib import Path
import types
import sys

# Load NetworkInterface directly to avoid heavy package imports
NI_PATH = Path(__file__).resolve().parents[2] / "src" / "caiengine" / "interfaces" / "network_interface.py"
spec_ni = importlib.util.spec_from_file_location("caiengine.interfaces.network_interface", NI_PATH)
network_interface = importlib.util.module_from_spec(spec_ni)
spec_ni.loader.exec_module(network_interface)
sys.modules['caiengine.interfaces'] = types.ModuleType('caiengine.interfaces')
sys.modules['caiengine.interfaces.network_interface'] = network_interface

# Import RoboIdConnection without triggering other imports
MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "caiengine" / "network" / "roboid_connection.py"
spec = importlib.util.spec_from_file_location("roboid_connection", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
RoboIdConnection = module.RoboIdConnection


class TestRoboIdConnection(unittest.TestCase):
    def test_send_receive(self):
        sock1, sock2 = socket.socketpair()
        conn1 = RoboIdConnection(sock1)
        conn2 = RoboIdConnection(sock2)

        received = []
        conn2.start_listening(lambda msg: received.append(msg))
        conn1.send("robot.transport@B#1", {"ping": "pong"})
        time.sleep(0.1)
        conn2.stop_listening()

        self.assertEqual(received[0]["message"], {"ping": "pong"})


if __name__ == "__main__":
    unittest.main()
