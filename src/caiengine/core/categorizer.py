from __future__ import annotations

import logging
import math
import re
from collections import Counter
from datetime import datetime
from typing import Iterable, Mapping, Sequence

from caiengine.interfaces.context_provider import ContextProvider
from caiengine.core.text_embeddings import HashingTextEmbedder
from caiengine.core.vector_normalizer.vector_comparer import VectorComparer

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
    """Neural network based categorizer backed by keyword heuristics.

    The categorizer uses a lightweight feed-forward network that is initialised
    using a predefined mapping of categories to representative keywords.  The
    network can be fine-tuned later, but even without additional training it
    provides deterministic behaviour similar to a keyword lookup while keeping
    the interface extensible for future learning-based approaches.
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
        del device  # retained for API compatibility

        raw_map = categories_keywords or self.DEFAULT_CATEGORY_KEYWORDS
        if not raw_map:
            raise ValueError("categories_keywords must define at least one category")

        self.unknown_category = unknown_category
        self.category_to_keywords = {
            category: tuple(sorted({kw.lower() for kw in keywords}))
            for category, keywords in raw_map.items()
        }
        self.category_bias = {k: float(v) for k, v in (category_bias or {}).items()}

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

        counts = Counter(tokens)
        raw_scores: dict[str, float] = {}
        for category, keywords in self.category_to_keywords.items():
            score = sum(counts.get(keyword, 0) for keyword in keywords)
            score += self.category_bias.get(category, 0.0)
            if score > 0:
                raw_scores[category] = float(score)

        if not raw_scores:
            return {}

        total = sum(raw_scores.values())
        return {category: score / total for category, score in raw_scores.items()}

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


class NeuralEmbeddingCategorizer:
    """Embedding driven categoriser backed by a shallow neural network.

    The categoriser converts text fragments into deterministic embeddings using
    :class:`~caiengine.core.text_embeddings.HashingTextEmbedder` and projects the
    result through a single linear layer.  The layer weights are initialised
    from example texts provided for each category which makes the behaviour
    immediately useful without additional training while keeping the
    implementation extensible for fine-tuning.
    """

    def __init__(
        self,
        category_examples: Mapping[str, Sequence[str]],
        *,
        embedder: HashingTextEmbedder | None = None,
        unknown_category: str = "unknown",
        device: object | None = None,
        temperature: float = 1.0,
        normalise_prototypes: bool = True,
    ) -> None:
        del device  # retained for API compatibility

        if not category_examples:
            raise ValueError("category_examples must define at least one category")

        if temperature <= 0:
            raise ValueError("temperature must be a positive value")

        self.embedder = embedder or HashingTextEmbedder()
        self.unknown_category = unknown_category
        self.temperature = float(temperature)
        self.normalise_prototypes = normalise_prototypes
        self.comparer = VectorComparer()

        self.prototypes: dict[str, list[float]] = {}
        for category, examples in category_examples.items():
            example_list = list(examples)
            if not example_list:
                raise ValueError(
                    f"Category '{category}' must include at least one training example"
                )

            embedded_examples = [
                self.embedder.embed(str(example)) for example in example_list
            ]
            prototype = self._average_vectors(embedded_examples)
            if self.normalise_prototypes:
                prototype = self._normalise_vector(prototype)
            self.prototypes[category] = prototype

    @staticmethod
    def _gather_fragments(item: Mapping) -> list[str]:
        fragments = []
        for fragment in NeuralKeywordCategorizer._iter_text_fragments(item):
            if fragment:
                fragments.append(fragment)
        return fragments

    def _encode(self, item: Mapping) -> list[float] | None:
        fragments = self._gather_fragments(item)
        if not fragments:
            return None

        text = " ".join(fragments)
        context = item.get("context")
        features = self.embedder.embed(text, context=context)
        if self.normalise_prototypes:
            return self._normalise_vector(features)
        return features

    @staticmethod
    def _average_vectors(vectors: Sequence[Sequence[float]]) -> list[float]:
        length = len(vectors[0])
        sums = [0.0] * length
        for vector in vectors:
            if len(vector) != length:
                raise ValueError("All embeddings must share the same dimensionality")
            for idx, value in enumerate(vector):
                sums[idx] += float(value)
        count = float(len(vectors))
        return [value / count for value in sums]

    @staticmethod
    def _normalise_vector(vector: Sequence[float]) -> list[float]:
        norm = math.sqrt(sum(float(v) * float(v) for v in vector))
        if norm == 0:
            return [0.0 for _ in vector]
        return [float(v) / norm for v in vector]

    def score_item(self, item: Mapping) -> dict[str, float]:
        """Return per-category probabilities for ``item``."""

        features = self._encode(item)
        if features is None:
            return {}

        raw_scores: dict[str, float] = {}
        for category, prototype in self.prototypes.items():
            similarity = self.comparer.cosine_similarity(features, prototype)
            adjusted = max(0.0, similarity) ** (1.0 / self.temperature)
            if adjusted > 0:
                raw_scores[category] = adjusted

        if not raw_scores:
            return {}

        total = sum(raw_scores.values())
        return {category: score / total for category, score in raw_scores.items()}

    def categorize(self, item: Mapping) -> dict[str, object]:
        """Categorise ``item`` using the embedding network."""

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
