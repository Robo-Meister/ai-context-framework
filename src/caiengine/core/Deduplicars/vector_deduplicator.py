from typing import List

import numpy as np

from caiengine.interfaces.filter_strategy import FilterStrategy
from caiengine.interfaces.deduplicator_strategy import DeduplicationStrategy
from typing import Optional, Callable
from datetime import datetime, timedelta


class VectorDeduplicator(DeduplicationStrategy):
    def __init__(
        self,
        filter_strategy: FilterStrategy,
        time_threshold_sec: int = 5,
        vector_similarity_threshold: float = 0.1,
        merge_rule: Optional[Callable[[dict, dict], dict]] = None,
    ):
        self.filter_strategy = filter_strategy
        self.vector_similarity_threshold = vector_similarity_threshold
        self.time_threshold = timedelta(seconds=time_threshold_sec)
        self.merge_rule = merge_rule or self.default_merge_rule

    def default_merge_rule(self, a: dict, b: dict) -> dict:
        if a.get("confidence", 0) > b.get("confidence", 0):
            return a
        elif b.get("confidence", 0) > a.get("confidence", 0):
            return b
        else:
            return (
                a
                if a.get("timestamp", datetime.min) >= b.get("timestamp", datetime.min)
                else b
            )

    def vector_similarity(self, v1, v2):
        """Return cosine distance between two vectors."""
        v1 = np.asarray(v1, dtype=float)
        v2 = np.asarray(v2, dtype=float)
        if v1.size == 0 or v2.size == 0:
            return 1.0
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 1.0
        cosine_sim = np.dot(v1, v2) / (norm1 * norm2)
        return float(1 - cosine_sim)

    def deduplicate(self, items: List[dict]) -> List[dict]:
        # Apply configured filter to numeric vectors in each item
        for item in items:
            vector = np.asarray(item.get("vector", []), dtype=float)
            if vector.size > 0:
                filtered_vector = self.filter_strategy.apply(vector)
                item["filtered_vector"] = filtered_vector
            else:
                item["filtered_vector"] = None

        unique = []
        for item in items:
            merged = False
            for i, u in enumerate(unique):
                # check time proximity
                time_diff = abs(
                    item.get("timestamp", datetime.min)
                    - u.get("timestamp", datetime.min)
                )
                if time_diff <= self.time_threshold:
                    # vector similarity check
                    v1 = item.get("filtered_vector")
                    v2 = u.get("filtered_vector")
                    if v1 is not None and v2 is not None:
                        if (
                            self.vector_similarity(v1, v2)
                            <= self.vector_similarity_threshold
                        ):
                            unique[i] = self.merge_rule(item, u)
                            merged = True
                            break
            if not merged:
                unique.append(item)

        return unique
