from typing import List, Optional, Tuple
from collections import defaultdict

from caiengine.core.categorizer import Categorizer
from caiengine.core.Deduplicars.fuzzy_deduplicator import FuzzyDeduplicator
from caiengine.interfaces.inference_engine import AIInferenceEngine
try:  # optional dependency
    from caiengine.core.learning.learning_manager import LearningManager
except Exception:  # pragma: no cover - optional dependency may be missing
    LearningManager = None  # type: ignore


class FeedbackPipeline:
    """Pipeline that categorizes context and feeds it directly into an inference
    engine with optional learning feedback. No fusion step is performed."""

    def __init__(
        self,
        context_provider,
        inference_engine: AIInferenceEngine,
        learning_manager: Optional[LearningManager] = None,
        time_threshold_sec: int = 5,
        fuzzy_threshold: float = 0.8,
        merge_rule=None,
    ):
        self.categorizer = Categorizer(context_provider)
        self.deduplicator = FuzzyDeduplicator(
            time_threshold_sec=time_threshold_sec,
            fuzzy_threshold=fuzzy_threshold,
            merge_rule=merge_rule,
        )
        self.inference_engine = inference_engine
        self.learning_manager = learning_manager

    def run(
        self,
        data_batch: List[dict],
        candidates: List[dict],
        feedback: Optional[List[Tuple[str, float]]] = None,
    ) -> List[dict]:
        """Process a batch of context items and optionally apply feedback.

        :param data_batch: Raw context items.
        :param candidates: Categorization candidates.
        :param feedback: Optional list of ``(log_line, corrected_label)`` tuples
            used to update the ``LearningManager``.
        :return: List of prediction dictionaries for each item.
        """
        categorized = defaultdict(list)
        for item in data_batch:
            category = self.categorizer.categorize(item, candidates)
            categorized[category].append(item)

        results = []
        for category, items in categorized.items():
            deduped = self.deduplicator.deduplicate(items)
            for item in deduped:
                item_copy = dict(item)
                item_copy["category"] = category
                prediction = self.inference_engine.predict(item_copy)
                results.append({
                    "category": category,
                    "prediction": prediction,
                    "item": item_copy,
                })

        if feedback and self.learning_manager:
            for log_line, label in feedback:
                self.learning_manager.learn_from_feedback(log_line, label)

        return results
