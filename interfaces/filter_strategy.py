from typing import List


class FilterStrategy:
    def apply(self, vector: List[float]) -> List[float]:
        raise NotImplementedError()
