from typing import List


class DeduplicationStrategy:
    def deduplicate(self, items: List[dict]) -> List[dict]:
        raise NotImplementedError()
