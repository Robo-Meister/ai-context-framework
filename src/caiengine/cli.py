import argparse
import importlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from caiengine.core import model_bundle, model_manager
from caiengine.objects.context_query import ContextQuery
from caiengine.objects.model_manifest import ModelManifest

DEFAULT_PROVIDER = "caiengine.providers.memory_context_provider.MemoryContextProvider"

logger = logging.getLogger(__name__)


def parse_provider_options(raw_options: str | None) -> dict | None:
    if raw_options is None:
        return None

    try:
        options = json.loads(raw_options)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Invalid JSON for --provider-options. Expected a JSON object, "
            'for example: --provider-options \'{"db_path": "context.db"}\''
        ) from exc

    if not isinstance(options, dict):
        raise ValueError("--provider-options must be a JSON object (key/value pairs).")

    return options


def load_provider(path: str, provider_options: str | None = None):
    try:
        module_name, class_name = path.rsplit(".", 1)
    except ValueError as exc:
        raise ValueError(
            f"Invalid provider path '{path}'. Expected format 'module.ClassName'."
        ) from exc

    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ImportError(f"Cannot import provider module '{module_name}'.") from exc

    try:
        cls = getattr(module, class_name)
    except AttributeError as exc:
        raise AttributeError(
            f"Provider class '{class_name}' not found in module '{module_name}'."
        ) from exc

    options = parse_provider_options(provider_options)
    if options is None:
        return cls()
    return cls(**options)


def cmd_add(args):
    provider = load_provider(args.provider, args.provider_options)
    payload = json.loads(args.payload)
    metadata = json.loads(args.metadata) if args.metadata else {}
    timestamp = datetime.fromisoformat(args.timestamp) if args.timestamp else datetime.utcnow()
    ctx_id = provider.ingest_context(
        payload,
        timestamp=timestamp,
        metadata=metadata,
        source_id=args.source_id,
        confidence=float(args.confidence),
        ttl=args.ttl,
    )
    logger.info(ctx_id)


def cmd_query(args):
    provider = load_provider(args.provider, args.provider_options)
    start = datetime.fromisoformat(args.start)
    end = datetime.fromisoformat(args.end)
    roles = args.roles.split(",") if args.roles else []
    query = ContextQuery(
        roles=roles,
        time_range=(start, end),
        scope=args.scope or "",
        data_type=args.data_type or "",
    )
    result = provider.get_context(query)
    logger.info(json.dumps(result, default=str, indent=2))


def cmd_model_load(args):
    model_manager.transport_model(args.source, args.dest)
    if args.version and not model_manager.check_version(args.dest, args.version):
        raise RuntimeError("Model version mismatch")


def cmd_model_migrate(args):
    model_manager.upgrade_schema(args.path, args.target_version)


def cmd_model_export(args):
    model_manager.transport_model(args.path, args.dest)


def cmd_model_bundle_fetch(args):
    model_manager.transport_bundle(args.source, args.dest)


def cmd_model_bundle_validate(args):
    errors = model_bundle.validate_model_bundle_zip(args.path)
    if errors:
        raise RuntimeError("Bundle validation failed: " + "; ".join(errors))


def cmd_model_bundle_export(args):
    if not args.from_torch:
        raise ValueError("bundle-export requires --from-torch module:function")

    factory = _load_callable(args.from_torch)
    model, example_input = factory()
    manifest = _load_manifest_for_bundle_export(args.manifest, args.from_torch)
    model_bundle.export_model_bundle_zip(model, example_input, manifest, args.dest)


def _load_callable(path: str):
    try:
        module_name, func_name = path.split(":", 1)
    except ValueError as exc:
        raise ValueError("--from-torch must use module:function format") from exc

    module = importlib.import_module(module_name)
    fn = getattr(module, func_name)
    if not callable(fn):
        raise ValueError(f"Callable not found for --from-torch: {path}")
    return fn


def _load_manifest_for_bundle_export(manifest_path: str | None, from_torch: str) -> ModelManifest:
    if manifest_path is None:
        return ModelManifest(model_name=from_torch, version="1.0")

    path = Path(manifest_path)
    with open(path, "r", encoding="utf-8") as fh:
        raw_text = fh.read()

    data: dict[str, Any] | None = None
    if path.suffix.lower() == ".json":
        data = json.loads(raw_text)
    else:
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError:
            raise RuntimeError("YAML manifest requires PyYAML to be installed")
        data = yaml.safe_load(raw_text)

    if not isinstance(data, dict):
        raise ValueError("Manifest must deserialize to a JSON/YAML mapping")
    return ModelManifest(**data)


def main(argv=None):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(prog="context")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help="Provider class path")
    parser.add_argument(
        "--provider-options",
        default=None,
        help="JSON object of kwargs passed into the provider constructor",
    )
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser(
        "add",
        help="Add context entry (supports constructor kwargs via --provider-options)",
        description="Add context entry. Use global --provider-options JSON to pass provider constructor kwargs.",
    )
    add_p.add_argument("--payload", required=True, help="JSON payload")
    add_p.add_argument("--metadata", default="{}", help="JSON metadata")
    add_p.add_argument("--timestamp", default=None, help="ISO timestamp")
    add_p.add_argument("--source-id", default="cli", help="Source identifier")
    add_p.add_argument("--confidence", default="1.0", help="Confidence score")
    add_p.add_argument("--ttl", type=int, default=None, help="TTL in seconds for cache retention")

    query_p = sub.add_parser(
        "query",
        help="Query context entries (supports constructor kwargs via --provider-options)",
        description="Query context entries. Use global --provider-options JSON to pass provider constructor kwargs.",
    )
    query_p.add_argument("--start", required=True, help="Start timestamp (ISO)")
    query_p.add_argument("--end", required=True, help="End timestamp (ISO)")
    query_p.add_argument("--roles", default="", help="Comma separated roles")
    query_p.add_argument("--scope", default="", help="Scope")
    query_p.add_argument("--data-type", default="", help="Data type")

    model_p = sub.add_parser("model", help="Model operations")
    model_sub = model_p.add_subparsers(dest="model_command")

    load_p = model_sub.add_parser("load", help="Load model from source")
    load_p.add_argument("--source", required=True, help="Source path or URL")
    load_p.add_argument("--dest", required=True, help="Destination path")
    load_p.add_argument("--version", default=None, help="Expected model version")

    migrate_p = model_sub.add_parser("migrate", help="Migrate model schema")
    migrate_p.add_argument("--path", required=True, help="Model file path")
    migrate_p.add_argument("--target-version", required=True, help="Target schema version")

    export_p = model_sub.add_parser("export", help="Export model to destination")
    export_p.add_argument("--path", required=True, help="Model file path")
    export_p.add_argument("--dest", required=True, help="Destination path")

    bundle_export_p = model_sub.add_parser("bundle-export", help="Export model bundle zip")
    bundle_export_p.add_argument("--dest", required=True, help="Destination bundle zip path")
    bundle_export_p.add_argument("--manifest", default=None, help="Manifest JSON/YAML path")
    bundle_export_p.add_argument(
        "--from-torch",
        default=None,
        help="Factory callable as module:function returning (model, example_input)",
    )

    bundle_validate_p = model_sub.add_parser("bundle-validate", help="Validate model bundle zip")
    bundle_validate_p.add_argument("--path", required=True, help="Bundle zip path")

    bundle_fetch_p = model_sub.add_parser("bundle-fetch", help="Fetch model bundle zip")
    bundle_fetch_p.add_argument("--source", required=True, help="Bundle source URL/path")
    bundle_fetch_p.add_argument("--dest", required=True, help="Destination bundle zip path")

    args = parser.parse_args(argv)

    try:
        parse_provider_options(args.provider_options)
    except ValueError as exc:
        parser.error(str(exc))

    if args.command == "add":
        cmd_add(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "model":
        if args.model_command == "load":
            cmd_model_load(args)
        elif args.model_command == "migrate":
            cmd_model_migrate(args)
        elif args.model_command == "export":
            cmd_model_export(args)
        elif args.model_command == "bundle-export":
            cmd_model_bundle_export(args)
        elif args.model_command == "bundle-validate":
            cmd_model_bundle_validate(args)
        elif args.model_command == "bundle-fetch":
            cmd_model_bundle_fetch(args)
        else:
            model_p.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
