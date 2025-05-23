import difflib
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


class Deduplicator:
    def __init__(
        self,
        time_threshold_sec: int = 5,
        fuzzy_threshold: float = 0.8,
        merge_rule: Optional[Callable[[dict, dict], dict]] = None,
    ):
        self.time_threshold = timedelta(seconds=time_threshold_sec)
        self.fuzzy_threshold = fuzzy_threshold
        self.merge_rule = merge_rule or self.default_merge_rule

    def payload_similarity(self, a: dict, b: dict) -> float:
        a_str = json.dumps(a, sort_keys=True)
        b_str = json.dumps(b, sort_keys=True)
        return difflib.SequenceMatcher(None, a_str, b_str).ratio()

    def default_merge_rule(self, a: dict, b: dict) -> dict:
        # Pick higher confidence or newer timestamp if equal
        if a.get('confidence', 0) > b.get('confidence', 0):
            return a
        elif b.get('confidence', 0) > a.get('confidence', 0):
            return b
        else:
            return a if a.get('timestamp', datetime.min) >= b.get('timestamp', datetime.min) else b

    def deduplicate(self, items: List[dict]) -> List[dict]:
        items_sorted = sorted(items, key=lambda x: x.get('timestamp', datetime.min))
        unique = []

        for item in items_sorted:
            merged = False
            for i, u in enumerate(unique):
                time_diff = abs(item.get('timestamp', datetime.min) - u.get('timestamp', datetime.min))
                if time_diff <= self.time_threshold:
                    similarity = self.payload_similarity(item.get('context', {}), u.get('context', {}))
                    if similarity >= self.fuzzy_threshold:
                        unique[i] = self.merge_rule(item, u)
                        merged = True
                        break
            if not merged:
                unique.append(item)

        return unique