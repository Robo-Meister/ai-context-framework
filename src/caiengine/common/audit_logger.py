import logging
from typing import Any, Dict, List, Optional

class AuditLogger:
    """Simple audit logger that records pipeline steps.

    Records are stored in-memory and also emitted via the standard
    :mod:`logging` module so applications can configure handlers as needed.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger("caiengine.audit")
        self.records: List[Dict[str, Any]] = []

    def log(self, pipeline: str, step: str, detail: Optional[Dict[str, Any]] = None) -> None:
        """Register a pipeline ``step`` with optional ``detail`` data."""
        entry: Dict[str, Any] = {"pipeline": pipeline, "step": step}
        if detail:
            entry["detail"] = detail
        self.records.append(entry)
        if detail:
            self.logger.info("%s - %s - %s", pipeline, step, detail)
        else:
            self.logger.info("%s - %s", pipeline, step)

    def get_records(self) -> List[Dict[str, Any]]:
        """Return all collected audit records."""
        return list(self.records)
