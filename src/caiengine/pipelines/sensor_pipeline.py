"""Pipeline specialized for sensor data with nested context layers.

This module provides ``SensorPipeline`` which mirrors
``ContextPipeline`` but explicitly targets scenarios where sensor or
environmental data arrives in nested context structures (for example,
``{"environment": {"camera": "cam1"}}``). It deduplicates events using
``FuzzyDeduplicator`` and fuses categorized results.
"""

from collections import defaultdict
from typing import List

from caiengine.core.categorizer import Categorizer
from caiengine.core.Deduplicars.fuzzy_deduplicator import FuzzyDeduplicator
from caiengine.core.fuser import Fuser
from caiengine.common import AuditLogger


class SensorPipeline:
    """Pipeline for processing sensor context data."""

    def __init__(self, context_provider, time_threshold_sec: int = 5,
                 fuzzy_threshold: float = 0.8, merge_rule=None, audit_logger: AuditLogger | None = None):
        self.categorizer = Categorizer(context_provider)
        self.deduplicator = FuzzyDeduplicator(
            time_threshold_sec=time_threshold_sec,
            fuzzy_threshold=fuzzy_threshold,
            merge_rule=merge_rule,
        )
        self.fuser = Fuser()
        self.audit_logger = audit_logger

    def run(self, data_batch: List[dict], candidates: List[dict]):
        """Deduplicate, categorize and fuse a batch of sensor events."""

        if self.audit_logger:
            self.audit_logger.log("SensorPipeline", "run_start", {"items": len(data_batch), "candidates": len(candidates)})

        categorized = defaultdict(list)
        for item in data_batch:
            key = self.categorizer.categorize(item, candidates)
            categorized[key].append(item)

        if self.audit_logger:
            self.audit_logger.log("SensorPipeline", "categorized", {"categories": len(categorized)})

        deduped = {
            key: self.deduplicator.deduplicate(items) for key, items in categorized.items()
        }

        if self.audit_logger:
            self.audit_logger.log("SensorPipeline", "deduplicated", {"categories": len(deduped)})

        fused = self.fuser.fuse(deduped)

        if self.audit_logger:
            self.audit_logger.log("SensorPipeline", "fused", {"result_count": len(fused)})

        return fused
