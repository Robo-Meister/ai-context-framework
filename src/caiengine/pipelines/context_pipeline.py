from collections import defaultdict
from typing import List

from caiengine.core.categorizer import Categorizer
from caiengine.core.Deduplicars.fuzzy_deduplicator import FuzzyDeduplicator
from caiengine.core.fuser import Fuser


class ContextPipeline:
    def __init__(self, context_provider, time_threshold_sec=5, fuzzy_threshold=0.8, merge_rule=None):
        self.categorizer = Categorizer(context_provider)
        self.deduplicator = FuzzyDeduplicator(
            time_threshold_sec=time_threshold_sec,
            fuzzy_threshold=fuzzy_threshold,
            merge_rule=merge_rule,
        )
        self.fuser = Fuser()

    def run(self, data_batch: List[dict], candidates: List[dict]):
        categorized = defaultdict(list)
        for item in data_batch:
            key = self.categorizer.categorize(item, candidates)
            categorized[key].append(item)

        deduped = {
            key: self.deduplicator.deduplicate(items) for key, items in categorized.items()
        }

        return self.fuser.fuse(deduped)
