import argparse
import json
import sys
import types
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from caiengine import cli
from caiengine.objects.context_query import ContextQuery


def _register_provider(monkeypatch, module_name, provider_cls):
    module = types.ModuleType(module_name)
    setattr(module, provider_cls.__name__, provider_cls)
    monkeypatch.setitem(sys.modules, module_name, module)
    return f"{module_name}.{provider_cls.__name__}"


def test_load_provider_invalid_path_raises_value_error():
    with pytest.raises(ValueError):
        cli.load_provider("invalidpath")


def test_cmd_add_ingests_context_with_expected_arguments(monkeypatch):
    captured = {}

    class DummyProvider:
        def ingest_context(self, payload, **kwargs):
            captured["payload"] = payload
            captured.update(kwargs)
            return "ctx-123"

    provider_path = _register_provider(monkeypatch, "test_cli_add", DummyProvider)
    payload = {"foo": "bar"}
    metadata = {"roles": ["analyst"], "extra": True}
    timestamp = datetime.utcnow().isoformat()

    args = SimpleNamespace(
        provider=provider_path,
        payload=json.dumps(payload),
        metadata=json.dumps(metadata),
        timestamp=timestamp,
        source_id="tester",
        confidence="0.75",
        ttl=60,
    )

    cli.cmd_add(args)

    assert captured["payload"] == payload
    assert captured["metadata"] == metadata
    assert captured["source_id"] == "tester"
    assert captured["confidence"] == pytest.approx(0.75)
    assert captured["ttl"] == 60
    assert captured["timestamp"].isoformat() == timestamp


def test_cmd_query_fetches_expected_context(monkeypatch):
    captured_query = {}
    returned = [{"context": "data"}]

    class QueryProvider:
        def get_context(self, query: ContextQuery):
            captured_query["query"] = query
            return returned

    provider_path = _register_provider(monkeypatch, "test_cli_query", QueryProvider)
    start = datetime.utcnow()
    end = start + timedelta(hours=1)

    args = SimpleNamespace(
        provider=provider_path,
        start=start.isoformat(),
        end=end.isoformat(),
        roles="alpha,beta",
        scope="global",
        data_type="json",
    )

    cli.cmd_query(args)

    query = captured_query["query"]
    assert isinstance(query, ContextQuery)
    assert query.roles == ["alpha", "beta"]
    assert query.time_range == (start, end)
    assert query.scope == "global"
    assert query.data_type == "json"


def test_cmd_model_load_validates_version(monkeypatch):
    transport_called = {}

    def fake_transport(source, dest):
        transport_called["args"] = (source, dest)

    def fake_check_version(dest, version):
        transport_called["checked_version"] = (dest, version)
        return False

    monkeypatch.setattr(cli.model_manager, "transport_model", fake_transport)
    monkeypatch.setattr(cli.model_manager, "check_version", fake_check_version)

    args = SimpleNamespace(source="src", dest="dst", version="1.0.0")

    with pytest.raises(RuntimeError):
        cli.cmd_model_load(args)

    assert transport_called["args"] == ("src", "dst")
    assert transport_called["checked_version"] == ("dst", "1.0.0")


def test_cmd_model_load_skips_version_check_when_not_provided(monkeypatch):
    called = {}

    def fake_transport(source, dest):
        called["args"] = (source, dest)

    def fail_check(*_args, **_kwargs):
        raise AssertionError("check_version should not be called")

    monkeypatch.setattr(cli.model_manager, "transport_model", fake_transport)
    monkeypatch.setattr(cli.model_manager, "check_version", fail_check)

    args = SimpleNamespace(source="src", dest="dst", version=None)
    cli.cmd_model_load(args)

    assert called["args"] == ("src", "dst")


def test_cmd_model_migrate_invokes_upgrade(monkeypatch):
    called = {}

    def fake_upgrade(path, version):
        called["args"] = (path, version)

    monkeypatch.setattr(cli.model_manager, "upgrade_schema", fake_upgrade)

    args = SimpleNamespace(path="model.bin", target_version="2")
    cli.cmd_model_migrate(args)

    assert called["args"] == ("model.bin", "2")


def test_cmd_model_export_invokes_transport(monkeypatch):
    called = {}

    def fake_transport(path, dest):
        called["args"] = (path, dest)

    monkeypatch.setattr(cli.model_manager, "transport_model", fake_transport)

    args = SimpleNamespace(path="model.bin", dest="out/")
    cli.cmd_model_export(args)

    assert called["args"] == ("model.bin", "out/")


def test_main_dispatches_add_command(monkeypatch):
    received_args = {}

    def fake_cmd_add(args):
        received_args["args"] = args

    monkeypatch.setattr(cli, "cmd_add", fake_cmd_add)

    cli.main([
        "--provider",
        "ignored.Provider",
        "add",
        "--payload",
        "{}",
    ])

    assert isinstance(received_args["args"], argparse.Namespace)
    assert received_args["args"].provider == "ignored.Provider"


def test_main_dispatches_model_export(monkeypatch):
    received_args = {}

    def fake_cmd_model_export(args):
        received_args["args"] = args

    monkeypatch.setattr(cli, "cmd_model_export", fake_cmd_model_export)

    cli.main([
        "model",
        "export",
        "--path",
        "model.bin",
        "--dest",
        "out.bin",
    ])

    assert received_args["args"].path == "model.bin"
    assert received_args["args"].dest == "out.bin"
