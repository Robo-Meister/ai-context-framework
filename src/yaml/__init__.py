"""A minimal :mod:`yaml` replacement used for the tests.

The real project uses PyYAML.  The unit tests only require ``safe_dump`` and
``safe_load`` to store small metadata dictionaries, so this stub serialises data
as JSON for simplicity.
"""

from __future__ import annotations

import json
from typing import Any, IO


def safe_dump(data: Any, stream: IO[str], **_: Any) -> None:
    json.dump(data, stream)


def safe_load(stream: IO[str] | str) -> Any:
    if isinstance(stream, str):
        return json.loads(stream) if stream else None
    return json.load(stream)


__all__ = ["safe_dump", "safe_load"]
