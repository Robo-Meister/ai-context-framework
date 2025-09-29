"""Tests for the hardened :mod:`SimpleNetworkMock` implementation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


def load_simple_network_mock():
    """Load ``SimpleNetworkMock`` without importing the full ``caiengine`` package."""

    root = Path(__file__).resolve().parents[2]
    package_root = root / "src/caiengine"
    interfaces_root = package_root / "interfaces"

    if "caiengine" not in sys.modules:
        pkg = ModuleType("caiengine")
        pkg.__path__ = [str(package_root)]
        sys.modules["caiengine"] = pkg

    if "caiengine.interfaces" not in sys.modules:
        interfaces_pkg = ModuleType("caiengine.interfaces")
        interfaces_pkg.__path__ = [str(interfaces_root)]
        sys.modules["caiengine.interfaces"] = interfaces_pkg

    iface_name = "caiengine.interfaces.network_interface"
    if iface_name not in sys.modules:
        iface_path = interfaces_root / "network_interface.py"
        iface_spec = importlib.util.spec_from_file_location(iface_name, iface_path)
        iface_module = importlib.util.module_from_spec(iface_spec)
        assert iface_spec and iface_spec.loader
        iface_spec.loader.exec_module(iface_module)
        sys.modules[iface_name] = iface_module
        sys.modules["caiengine.interfaces"].network_interface = iface_module

    module_path = package_root / "network/simple_network.py"
    spec = importlib.util.spec_from_file_location("simple_network_module", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader  # for mypy / type checkers
    spec.loader.exec_module(module)
    return module.SimpleNetworkMock


SimpleNetworkMock = load_simple_network_mock()


def test_simple_network_collects_basic_metrics():
    net = SimpleNetworkMock()

    assert net.stats()["sent"] == 0

    assert net.send("node-1", {"ping": "pong"}) is True
    assert net.broadcast({"event": "online"}) is True

    assert net.receive() == ("node-1", {"ping": "pong"})
    assert net.receive() == ("broadcast", {"event": "online"})
    assert net.receive() is None

    stats = net.stats()
    assert stats["sent"] == 1
    assert stats["broadcast"] == 1
    assert stats["received"] == 2
    assert stats["queue_size"] == 0
    assert stats["last_activity"] is not None
    assert stats["last_latency_ms"] is not None


def test_simple_network_validates_payload_types():
    net = SimpleNetworkMock()

    with pytest.raises(ValueError):
        net.send("node-1", ["not", "a", "dict"])

    with pytest.raises(ValueError):
        net.send("", {"ok": True})


def test_simple_network_drops_messages_when_queue_full():
    net = SimpleNetworkMock(max_queue=1)

    assert net.send("node-1", {"seq": 1}) is True
    assert net.send("node-2", {"seq": 2}) is False

    stats = net.stats()
    assert stats["sent"] == 1
    assert stats["dropped"] == 1
    assert stats["queue_size"] == 1
    assert stats["last_error"] == "queue_full"

    assert net.receive() == ("node-1", {"seq": 1})
    assert net.receive() is None
