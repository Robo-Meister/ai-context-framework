from datetime import datetime
from typing import List

from scipy.spatial.distance import cosine
import numpy as np

from core.filters.kalman_filter import KalmanFilter
from interfaces.deduplicator_strategy import DeduplicationStrategy


class VectorDeduplicator(DeduplicationStrategy):
    def __init__(self, kalman_filter: KalmanFilter, vector_similarity_threshold=0.1, **kwargs):
        super().__init__(**kwargs)
        self.kalman_filter = kalman_filter
        self.vector_similarity_threshold = vector_similarity_threshold

    def vector_similarity(self, v1, v2):
        # cosine similarity distance (0=identical)
        return cosine(v1, v2)

    def deduplicate(self, items: List[dict]) -> List[dict]:
        # Apply Kalman filter to numeric vectors in each item
        for item in items:
            vector = np.array(item.get('vector', []))
            if vector.size > 0:
                filtered_vector = self.kalman_filter.apply(vector)
                item['filtered_vector'] = filtered_vector
            else:
                item['filtered_vector'] = None

        unique = []
        for item in items:
            merged = False
            for i, u in enumerate(unique):
                # check time proximity
                time_diff = abs(item.get('timestamp', datetime.min) - u.get('timestamp', datetime.min))
                if time_diff <= self.time_threshold:
                    # vector similarity check
                    v1 = item.get('filtered_vector')
                    v2 = u.get('filtered_vector')
                    if v1 is not None and v2 is not None:
                        if self.vector_similarity(v1, v2) <= self.vector_similarity_threshold:
                            unique[i] = self.merge_rule(item, u)
                            merged = True
                            break
            if not merged:
                unique.append(item)

        return unique
