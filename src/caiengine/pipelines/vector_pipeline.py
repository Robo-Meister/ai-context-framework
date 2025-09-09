from collections import defaultdict
from typing import List

from caiengine.core.categorizer import Categorizer
from caiengine.core.Deduplicars.vector_deduplicator import VectorDeduplicator
from caiengine.core.filters.kalman_filter import KalmanFilter
from caiengine.interfaces.filter_strategy import FilterStrategy
from caiengine.core.fuser import Fuser
from caiengine.common import AuditLogger


class VectorPipeline:
    """Pipeline that deduplicates using vector similarity before fusion."""

    def __init__(
        self,
        context_provider,
        vector_dim: int,
        filter_strategy: FilterStrategy | None = None,
        time_threshold_sec: int = 5,
        vector_similarity_threshold: float = 0.1,
        merge_rule=None,
        audit_logger: AuditLogger | None = None,
    ):
        self.categorizer = Categorizer(context_provider)
        filter_strategy = filter_strategy or KalmanFilter(vector_dim)
        self.deduplicator = VectorDeduplicator(
            filter_strategy=filter_strategy,
            time_threshold_sec=time_threshold_sec,
            vector_similarity_threshold=vector_similarity_threshold,
            merge_rule=merge_rule,
        )
        self.fuser = Fuser()
        self.audit_logger = audit_logger

    def run(self, data_batch: List[dict], candidates: List[dict]):
        if self.audit_logger:
            self.audit_logger.log("VectorPipeline", "run_start", {"items": len(data_batch), "candidates": len(candidates)})

        categorized = defaultdict(list)
        for item in data_batch:
            key = self.categorizer.categorize(item, candidates)
            categorized[key].append(item)

        if self.audit_logger:
            self.audit_logger.log("VectorPipeline", "categorized", {"categories": len(categorized)})

        deduped = {
            key: self.deduplicator.deduplicate(items)
            for key, items in categorized.items()
        }

        if self.audit_logger:
            self.audit_logger.log("VectorPipeline", "deduplicated", {"categories": len(deduped)})

        fused = self.fuser.fuse(deduped)

        if self.audit_logger:
            self.audit_logger.log("VectorPipeline", "fused", {"result_count": len(fused)})

        return fused
