from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Iterable, Mapping, Sequence

from caiengine.interfaces.context_provider import ContextProvider

logger = logging.getLogger(__name__)


class Categorizer:
    """Rule-based categorizer that compares context layers."""

    def __init__(self, context_provider: ContextProvider):
        self.context_provider = context_provider

    def _get_time_bucket(self, dt: datetime) -> str:
        # Example bucket: "Mon_09" = Monday 9am hour
        weekday = dt.strftime("%a")  # Mon, Tue, Wed, ...
        hour = dt.hour
        return f"{weekday}_{hour:02d}"

    def categorize(self, input_item: dict, candidates: list[dict]) -> str:
        """Return the best matching candidate category for ``input_item``."""

        best_match = None
        best_score = 0.0

        for candidate in candidates:
            match_score = self.compare_layers(
                input_item["context"], candidate["context"]
            )
            adjusted_weight = self.context_provider.get_adjusted_weight(
                candidate["base_weight"], candidate["context"]
            )
            total_score = match_score * adjusted_weight

            if total_score > best_score:
                best_score = total_score
                best_match = candidate["category"]

        return best_match or "unknown"

    def _flatten(self, ctx: dict, prefix: str = "") -> dict:
        flat = {}
        for key, value in ctx.items():
            if isinstance(value, dict):
                flat.update(self._flatten(value, prefix + key + "."))
            else:
                flat[prefix + key] = value
        return flat

    def compare_layers(self, ctx1: dict, ctx2: dict) -> float:
        """Return ratio of matching context layers (supports sublayers)."""

        f1 = self._flatten(ctx1)
        f2 = self._flatten(ctx2)
        keys = set(f1.keys()) | set(f2.keys())
        if not keys:
            return 0.0
        matched = sum(1 for key in keys if f1.get(key) == f2.get(key))
        return matched / len(keys)


class NeuralKeywordCategorizer:
    """Keyword driven categorizer with an interface compatible with the
    original neural implementation.

    The production project uses PyTorch for this component.  To keep the test
    environment lightweight we replace the neural network with a deterministic
    keyword counter that exposes the same public methods.  The behaviour is
    intentionally simple yet deterministic which is sufficient for the unit
    tests that focus on the surrounding pipeline logic.
    """

    DEFAULT_CATEGORY_KEYWORDS: Mapping[str, Sequence[str]] = {
        "sales": ("deal", "prospect", "pipeline", "opportunity"),
        "support": ("ticket", "issue", "bug", "outage"),
        "marketing": ("campaign", "lead", "promotion", "brand"),
        "finance": ("invoice", "payment", "billing", "revenue"),
        "product": ("feature", "roadmap", "release", "backlog"),
    }

    def __init__(
        self,
        categories_keywords: Mapping[str, Sequence[str]] | None = None,
        *,
        unknown_category: str = "unknown",
        device: object | None = None,
        category_bias: Mapping[str, float] | None = None,
    ) -> None:
        self.unknown_category = unknown_category

        raw_map = categories_keywords or self.DEFAULT_CATEGORY_KEYWORDS
        if not raw_map:
            raise ValueError("categories_keywords must define at least one category")

        self.category_to_keywords = {
            category: tuple(sorted({kw.lower() for kw in keywords}))
            for category, keywords in raw_map.items()
        }
        self.categories = tuple(self.category_to_keywords.keys())
        self.keyword_to_index = self._build_vocabulary(self.category_to_keywords)
        self.category_bias = dict(category_bias or {})

    @staticmethod
    def _build_vocabulary(
        category_map: Mapping[str, Sequence[str]]
    ) -> Mapping[str, int]:
        vocab = {}
        for keywords in category_map.values():
            for keyword in keywords:
                if keyword not in vocab:
                    vocab[keyword] = len(vocab)
        if not vocab:
            raise ValueError("No keywords provided for neural categorizer")
        return vocab

    @staticmethod
    def _iter_text_fragments(item: Mapping) -> Iterable[str]:
        if not item:
            return []

        def _walk(value: object) -> Iterable[str]:
            if isinstance(value, str):
                yield value
            elif isinstance(value, Mapping):
                for inner in value.values():
                    yield from _walk(inner)
            elif isinstance(value, (list, tuple, set)):
                for inner in value:
                    yield from _walk(inner)

        yield from _walk(item.get("content"))
        yield from _walk(item.get("context"))
        yield from _walk(item.get("keywords"))
        yield from _walk(item.get("tags"))

    @staticmethod
    def _tokenise(text: str) -> Iterable[str]:
        return re.findall(r"[\w']+", text.lower())

    def score_item(self, item: Mapping) -> dict[str, float]:
        """Return per-category probabilities for the provided ``item``."""

        fragments = list(self._iter_text_fragments(item))
        tokens: list[str] = []
        for fragment in fragments:
            tokens.extend(self._tokenise(fragment))

        if not tokens:
            return {}
        counts = Counter(token for token in tokens if token in self.keyword_to_index)
        scores: dict[str, float] = {}
        for category, keywords in self.category_to_keywords.items():
            score = sum(float(counts.get(keyword, 0)) for keyword in keywords)
            score += float(self.category_bias.get(category, 0.0))
            if score > 0:
                scores[category] = score

        total = sum(scores.values())
        if total <= 0:
            return {}

        return {category: value / total for category, value in scores.items()}

    def categorize(self, item: Mapping) -> dict[str, object]:
        """Categorise ``item`` and return the best match with confidences."""

        scores = self.score_item(item)
        if not scores:
            return {
                "category": self.unknown_category,
                "confidence": 0.0,
                "scores": {},
            }

        best_category = max(scores, key=scores.get)
        return {
            "category": best_category,
            "confidence": scores[best_category],
            "scores": scores,
        }
