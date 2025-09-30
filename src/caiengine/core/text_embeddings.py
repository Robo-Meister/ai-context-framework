"""Utilities for text embedding, categorisation and comparison.

The helpers in this module provide a lightweight approach for embedding
free-form text into deterministic numeric vectors so it can be compared with
existing context similarity tooling.  They also include a keyword driven
categoriser that mirrors the behaviour of :class:`NeuralKeywordCategorizer`
without depending on the optional PyTorch dependency, making the
functionality available in lightweight deployments and unit tests.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from itertools import zip_longest
from typing import Iterable, Mapping, Sequence

try:  # pragma: no cover - optional dependency proxy
    from caiengine.core.vector_normalizer.vector_comparer import VectorComparer
except Exception:  # pragma: no cover - fallback when optional deps missing
    class VectorComparer:  # type: ignore[override]
        """Lightweight fallback comparer mirroring :class:`VectorComparer`."""

        def __init__(self, weights: Sequence[float] | None = None) -> None:
            self.weights = list(weights) if weights is not None else None

        def cosine_similarity(self, vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
            a = self._weighted(vec_a)
            b = self._weighted(vec_b)
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(y * y for y in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        def _weighted(self, vec: Sequence[float]) -> list[float]:
            values = [float(v) for v in vec]
            if self.weights is None:
                return values
            return [v * float(w) for v, w in zip_longest(values, self.weights, fillvalue=1.0)]


_TOKEN_PATTERN = re.compile(r"[\w']+")


def _iter_text_fragments(value: object) -> Iterable[str]:
    """Yield text fragments from ``value`` recursively.

    The helper accepts nested containers (mappings, sequences) and extracts
    any strings they contain.  Non-string values are ignored.  ``None`` is
    treated as an empty iterable.
    """

    if value is None:
        return

    if isinstance(value, str):
        yield value
        return

    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_text_fragments(nested)
        return

    if isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _iter_text_fragments(nested)
        return


def _tokenise(text: str) -> Iterable[str]:
    for token in _TOKEN_PATTERN.findall(text.lower()):
        yield token


class SimpleTextCategorizer:
    """Keyword driven categoriser for plain text inputs.

    Parameters
    ----------
    categories_keywords:
        Mapping of category names to keywords.  When not provided the default
        categories mirror those of :class:`NeuralKeywordCategorizer` so the
        return values align with the richer implementation when PyTorch is
        available.
    unknown_category:
        Name of the category returned when no keywords match.
    """

    DEFAULT_CATEGORY_KEYWORDS: Mapping[str, Sequence[str]] = {
        "sales": ("deal", "prospect", "pipeline", "opportunity"),
        "support": ("ticket", "issue", "bug", "outage", "incident"),
        "marketing": ("campaign", "lead", "promotion", "brand"),
        "finance": ("invoice", "payment", "billing", "revenue"),
        "product": ("feature", "roadmap", "release", "backlog"),
    }

    def __init__(
        self,
        categories_keywords: Mapping[str, Sequence[str]] | None = None,
        *,
        unknown_category: str = "unknown",
    ) -> None:
        raw_map = categories_keywords or self.DEFAULT_CATEGORY_KEYWORDS
        if not raw_map:
            raise ValueError("categories_keywords must define at least one category")

        self.category_to_keywords = {
            category: tuple(sorted({kw.lower() for kw in keywords}))
            for category, keywords in raw_map.items()
        }
        self.unknown_category = unknown_category

    def categorize(
        self, text: str, context: Iterable[object] | None = None
    ) -> dict[str, object]:
        tokens = list(_tokenise(text or ""))
        if context is not None:
            for fragment in _iter_text_fragments(context):
                tokens.extend(_tokenise(fragment))

        if not tokens:
            return {
                "category": self.unknown_category,
                "confidence": 0.0,
                "scores": {},
            }

        counter = Counter(tokens)
        raw_scores: dict[str, float] = {}
        for category, keywords in self.category_to_keywords.items():
            score = float(sum(counter.get(keyword, 0) for keyword in keywords))
            if score:
                raw_scores[category] = score

        if not raw_scores:
            return {
                "category": self.unknown_category,
                "confidence": 0.0,
                "scores": {},
            }

        total = sum(raw_scores.values())
        scores = {category: score / total for category, score in raw_scores.items()}
        best_category = max(scores, key=scores.get)
        return {
            "category": best_category,
            "confidence": scores[best_category],
            "scores": scores,
        }


class HashingTextEmbedder:
    """Embed text into a deterministic numeric vector using hashing."""

    def __init__(
        self,
        *,
        dimension: int = 128,
        context_weight: float = 0.5,
        normalise: bool = True,
    ) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be a positive integer")
        self.dimension = int(dimension)
        self.context_weight = float(context_weight)
        self.normalise = normalise

    def embed(
        self, text: str, *, context: Iterable[object] | None = None
    ) -> list[float]:
        vector = [0.0] * self.dimension

        for token in _tokenise(text or ""):
            index = self._bucket(token)
            vector[index] += 1.0

        if context is not None and self.context_weight:
            weight = self.context_weight
            for fragment in _iter_text_fragments(context):
                for token in _tokenise(fragment):
                    index = self._bucket(token)
                    vector[index] += weight

        if self.normalise:
            return self._normalise(vector)
        return vector

    def _bucket(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        return value % self.dimension

    def _normalise(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class TextEmbeddingComparer:
    """High level helper combining categorisation, embedding and comparison."""

    def __init__(
        self,
        *,
        embedder: HashingTextEmbedder | None = None,
        comparer: VectorComparer | None = None,
        categorizer: SimpleTextCategorizer | None = None,
    ) -> None:
        self.embedder = embedder or HashingTextEmbedder()
        self.comparer = comparer or VectorComparer()
        self.categorizer = categorizer or SimpleTextCategorizer()

    def embed(self, text: str, *, context: Iterable[object] | None = None) -> list[float]:
        return self.embedder.embed(text, context=context)

    def categorize(
        self, text: str, *, context: Iterable[object] | None = None
    ) -> dict[str, object]:
        return self.categorizer.categorize(text, context)

    def compare(
        self,
        text_a: str,
        text_b: str,
        *,
        context_a: Iterable[object] | None = None,
        context_b: Iterable[object] | None = None,
    ) -> dict[str, object]:
        embedding_a = self.embed(text_a, context=context_a)
        embedding_b = self.embed(text_b, context=context_b)

        similarity = self.comparer.cosine_similarity(embedding_a, embedding_b)

        return {
            "similarity": similarity,
            "embedding_a": embedding_a,
            "embedding_b": embedding_b,
            "category_a": self.categorize(text_a, context=context_a),
            "category_b": self.categorize(text_b, context=context_b),
        }

    def compare_embeddings(self, vector_a: Sequence[float], vector_b: Sequence[float]) -> float:
        return self.comparer.cosine_similarity(list(vector_a), list(vector_b))
