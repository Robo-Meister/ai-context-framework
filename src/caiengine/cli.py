import argparse
import json
import importlib
from datetime import datetime
from caiengine.objects.context_query import ContextQuery

DEFAULT_PROVIDER = "providers.memory_context_provider.MemoryContextProvider"

def load_provider(path: str):
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls()

def cmd_add(args):
    provider = load_provider(args.provider)
    payload = json.loads(args.payload)
    metadata = json.loads(args.metadata) if args.metadata else {}
    timestamp = datetime.fromisoformat(args.timestamp) if args.timestamp else datetime.utcnow()
    ctx_id = provider.ingest_context(
        payload,
        timestamp=timestamp,
        metadata=metadata,
        source_id=args.source_id,
        confidence=float(args.confidence),
    )
    print(ctx_id)

def cmd_query(args):
    provider = load_provider(args.provider)
    start = datetime.fromisoformat(args.start)
    end = datetime.fromisoformat(args.end)
    roles = args.roles.split(",") if args.roles else []
    query = ContextQuery(roles=roles, time_range=(start, end), scope=args.scope or "", data_type=args.data_type or "")
    result = provider.get_context(query)
    print(json.dumps(result, default=str, indent=2))

def main(argv=None):
    parser = argparse.ArgumentParser(prog="context")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help="Provider class path")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Add context entry")
    add_p.add_argument("--payload", required=True, help="JSON payload")
    add_p.add_argument("--metadata", default="{}", help="JSON metadata")
    add_p.add_argument("--timestamp", default=None, help="ISO timestamp")
    add_p.add_argument("--source-id", default="cli", help="Source identifier")
    add_p.add_argument("--confidence", default="1.0", help="Confidence score")

    query_p = sub.add_parser("query", help="Query context entries")
    query_p.add_argument("--start", required=True, help="Start timestamp (ISO)")
    query_p.add_argument("--end", required=True, help="End timestamp (ISO)")
    query_p.add_argument("--roles", default="", help="Comma separated roles")
    query_p.add_argument("--scope", default="", help="Scope")
    query_p.add_argument("--data-type", default="", help="Data type")

    args = parser.parse_args(argv)

    if args.command == "add":
        cmd_add(args)
    elif args.command == "query":
        cmd_query(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
