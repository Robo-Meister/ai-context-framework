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
        provider_options=None,
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
        provider_options=None,
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


def test_load_provider_applies_provider_options(monkeypatch):
    captured = {}

    class ConfigurableProvider:
        def __init__(self, **kwargs):
            captured["kwargs"] = kwargs

    provider_path = _register_provider(monkeypatch, "test_cli_options", ConfigurableProvider)

    cli.load_provider(provider_path, '{"db_path": "/tmp/context.sqlite"}')

    assert captured["kwargs"] == {"db_path": "/tmp/context.sqlite"}


def test_load_provider_without_options_preserves_no_arg_instantiation(monkeypatch):
    captured = {}

    class LegacyProvider:
        def __init__(self):
            captured["constructed"] = True

    provider_path = _register_provider(monkeypatch, "test_cli_legacy", LegacyProvider)

    cli.load_provider(provider_path)

    assert captured["constructed"] is True


def test_load_provider_supports_sqlite_provider_options(monkeypatch, tmp_path):
    db_file = tmp_path / "context.db"
    captured = {}

    class SQLiteContextProvider:
        def __init__(self, db_path=":memory:"):
            captured["db_path"] = db_path

    provider_path = _register_provider(
        monkeypatch,
        "test_sqlite_provider_options",
        SQLiteContextProvider,
    )

    cli.load_provider(provider_path, json.dumps({"db_path": str(db_file)}))

    assert captured["db_path"] == str(db_file)


def test_main_reports_user_friendly_provider_options_json_error(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main([
            "--provider-options",
            "{not-valid-json}",
            "add",
            "--payload",
            "{}",
        ])

    assert exc_info.value.code == 2
    stderr = capsys.readouterr().err
    assert "Invalid JSON for --provider-options" in stderr


def test_cmd_model_bundle_validate_passes_when_no_errors(monkeypatch):
    called = {}

    def fake_validate(path):
        called["path"] = path
        return []

    monkeypatch.setattr(cli.model_bundle, "validate_model_bundle_zip", fake_validate)

    cli.cmd_model_bundle_validate(SimpleNamespace(path="bundle.zip"))

    assert called["path"] == "bundle.zip"


def test_cmd_model_bundle_validate_raises_on_errors(monkeypatch):
    def fake_validate(_path):
        return ["missing model.onnx"]

    monkeypatch.setattr(cli.model_bundle, "validate_model_bundle_zip", fake_validate)

    with pytest.raises(RuntimeError, match="Bundle validation failed"):
        cli.cmd_model_bundle_validate(SimpleNamespace(path="bad.zip"))


def test_cmd_model_bundle_fetch_invokes_transport_bundle(monkeypatch):
    called = {}

    def fake_transport(src, dest):
        called["args"] = (src, dest)

    monkeypatch.setattr(cli.model_manager, "transport_bundle", fake_transport)

    cli.cmd_model_bundle_fetch(SimpleNamespace(source="s", dest="d.zip"))

    assert called["args"] == ("s", "d.zip")


def test_main_dispatches_model_bundle_validate(monkeypatch):
    captured = {}

    def fake_cmd(args):
        captured["path"] = args.path

    monkeypatch.setattr(cli, "cmd_model_bundle_validate", fake_cmd)

    cli.main(["model", "bundle-validate", "--path", "bundle.zip"])

    assert captured["path"] == "bundle.zip"
