import importlib.util
from pathlib import Path
import sys

MODULE_PATH = Path(__file__).resolve().parents[2]
AN_PATH = MODULE_PATH / "src" / "caiengine" / "network" / "agent_network.py"
spec = importlib.util.spec_from_file_location(
    "caiengine.network.agent_network", AN_PATH
)
agent_network = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_network)
sys.modules["caiengine.network.agent_network"] = agent_network
AgentNetwork = agent_network.AgentNetwork


def test_connect_and_relationship():
    net = AgentNetwork()
    net.connect("a", "b", weight=0.5)

    assert net.relationship("a", "b") == 0.5
    assert net.relationship("b", "a") == 0.5
    assert set(net.neighbors("a")) == {"b"}
    assert set(net.neighbors("b")) == {"a"}


def test_disconnect_and_remove_agent():
    net = AgentNetwork()
    net.connect("a", "b")
    net.connect("b", "c")

    net.disconnect("a", "b")
    assert net.relationship("a", "b") is None

    net.remove_agent("b")
    assert "b" not in set(net.neighbors("c"))
    assert net.relationship("b", "c") is None
