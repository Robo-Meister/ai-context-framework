from collections import defaultdict
from typing import List

from ContextAi.core.categorizer import Categorizer
from ContextAi.core.deduplicator import Deduplicator
from ContextAi.core.fuser import Fuser


class ContextPipeline:
    def __init__(self, context_provider, time_threshold_sec=5, fuzzy_threshold=0.8, merge_rule=None):
        self.categorizer = Categorizer(context_provider)
        self.deduplicator = Deduplicator(time_threshold_sec, fuzzy_threshold, merge_rule)
        self.fuser = Fuser()

    def run(self, data_batch: List[dict], candidates: List[dict]):
        deduped = self.deduplicator.deduplicate(data_batch)
        categorized = defaultdict(list)
        for item in deduped:
            key = self.categorizer.categorize(item, candidates)
            categorized[key].append(item)
        return self.fuser.fuse(categorized)
