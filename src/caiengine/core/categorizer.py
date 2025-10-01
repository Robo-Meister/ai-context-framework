from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Iterable, Mapping, Sequence

try:  # pragma: no cover - optional dependency
    import torch
    from torch import nn
    from torch.nn import functional as F
except ImportError:  # pragma: no cover - optional dependency
    torch = None
    nn = None
    F = None

from caiengine.interfaces.context_provider import ContextProvider
from caiengine.core.text_embeddings import HashingTextEmbedder

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
        device: str | torch.device | None = None,
        category_bias: Mapping[str, float] | None = None,
    ) -> None:
        if torch is None:  # pragma: no cover - defensive guard
            raise ImportError("PyTorch is required for NeuralKeywordCategorizer")

        self.device = torch.device(device or "cpu")
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

        self.model = nn.Linear(len(self.keyword_to_index), len(self.categories))
        self.model.to(self.device)
        self.model.eval()

        self._initialise_weights(category_bias)

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

    def _initialise_weights(
        self, category_bias: Mapping[str, float] | None
    ) -> None:
        with torch.no_grad():
            self.model.weight.zero_()
            self.model.bias.zero_()

            for category, keywords in self.category_to_keywords.items():
                category_idx = self.categories.index(category)
                for keyword in keywords:
                    keyword_idx = self.keyword_to_index[keyword]
                    self.model.weight[category_idx, keyword_idx] = 1.0

                if category_bias and category in category_bias:
                    self.model.bias[category_idx] = category_bias[category]

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

    def _encode(self, tokens: Iterable[str]) -> torch.Tensor:
        counts = Counter(token for token in tokens if token in self.keyword_to_index)
        vector = torch.zeros(len(self.keyword_to_index), dtype=torch.float32)
        for token, count in counts.items():
            vector[self.keyword_to_index[token]] = float(count)
        return vector.to(self.device)

    def score_item(self, item: Mapping) -> dict[str, float]:
        """Return per-category probabilities for the provided ``item``."""

        fragments = list(self._iter_text_fragments(item))
        tokens: list[str] = []
        for fragment in fragments:
            tokens.extend(self._tokenise(fragment))

        if not tokens:
            return {}

        features = self._encode(tokens)

        with torch.no_grad():
            logits = self.model(features)
            probabilities = torch.softmax(logits, dim=0)

        return {
            category: probabilities[idx].item()
            for idx, category in enumerate(self.categories)
        }

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
        device: str | torch.device | None = None,
        temperature: float = 1.0,
        normalise_prototypes: bool = True,
    ) -> None:
        if torch is None or nn is None or F is None:  # pragma: no cover - guard
            raise ImportError("PyTorch is required for NeuralEmbeddingCategorizer")

        if not category_examples:
            raise ValueError("category_examples must define at least one category")

        if temperature <= 0:
            raise ValueError("temperature must be a positive value")

        self.device = torch.device(device or "cpu")
        self.embedder = embedder or HashingTextEmbedder()
        self.unknown_category = unknown_category
        self.temperature = float(temperature)

        categories: list[str] = []
        prototype_vectors: list[torch.Tensor] = []

        for category, examples in category_examples.items():
            example_list = list(examples)
            if not example_list:
                raise ValueError(
                    f"Category '{category}' must include at least one training example"
                )

            embedded_examples: list[torch.Tensor] = []
            for example in example_list:
                vector = torch.tensor(
                    self.embedder.embed(str(example)), dtype=torch.float32
                )
                embedded_examples.append(vector)

            stacked = torch.stack(embedded_examples)
            prototype = stacked.mean(dim=0)
            if normalise_prototypes:
                norm = torch.linalg.vector_norm(prototype)
                if norm > 0:
                    prototype = prototype / norm

            categories.append(category)
            prototype_vectors.append(prototype)

        weight = torch.stack(prototype_vectors)

        self.categories = tuple(categories)
        self.model = nn.Linear(weight.shape[1], len(self.categories), bias=False)
        self.model.to(self.device)
        self.model.eval()

        with torch.no_grad():
            self.model.weight.copy_(weight.to(self.device))

    @staticmethod
    def _gather_fragments(item: Mapping) -> list[str]:
        fragments = []
        for fragment in NeuralKeywordCategorizer._iter_text_fragments(item):
            if fragment:
                fragments.append(fragment)
        return fragments

    def _encode(self, item: Mapping) -> torch.Tensor | None:
        fragments = self._gather_fragments(item)
        if not fragments:
            return None

        text = " ".join(fragments)
        context = item.get("context")
        features = self.embedder.embed(text, context=context)
        tensor = torch.tensor(features, dtype=torch.float32, device=self.device)
        return tensor

    def score_item(self, item: Mapping) -> dict[str, float]:
        """Return per-category probabilities for ``item``."""

        features = self._encode(item)
        if features is None:
            return {}

        with torch.no_grad():
            logits = self.model(features)
            probabilities = F.softmax(logits / self.temperature, dim=0)

        return {
            category: probabilities[idx].item()
            for idx, category in enumerate(self.categories)
        }

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
