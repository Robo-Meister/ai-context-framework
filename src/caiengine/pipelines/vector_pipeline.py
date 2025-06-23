from collections import defaultdict
from typing import List

from caiengine.core.categorizer import Categorizer
from caiengine.core.Deduplicars.vector_deduplicator import VectorDeduplicator
from caiengine.core.filters.kalman_filter import KalmanFilter
from caiengine.interfaces.filter_strategy import FilterStrategy
from caiengine.core.fuser import Fuser


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

    def run(self, data_batch: List[dict], candidates: List[dict]):
        categorized = defaultdict(list)
        for item in data_batch:
            key = self.categorizer.categorize(item, candidates)
            categorized[key].append(item)

        deduped = {
            key: self.deduplicator.deduplicate(items)
            for key, items in categorized.items()
        }

        return self.fuser.fuse(deduped)
