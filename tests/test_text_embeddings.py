import math
import os

os.environ.setdefault("CAIENGINE_LIGHT_IMPORT", "1")

from caiengine.core.text_embeddings import (
    HashingTextEmbedder,
    SimpleTextCategorizer,
    TextEmbeddingComparer,
)


def test_hashing_text_embedder_is_deterministic() -> None:
    embedder = HashingTextEmbedder(dimension=32, normalise=False)

    first = embedder.embed("Support ticket resolved successfully")
    second = embedder.embed("Support ticket resolved successfully")

    assert first == second
    assert len(first) == 32


def test_hashing_text_embedder_uses_context() -> None:
    embedder = HashingTextEmbedder(dimension=16, normalise=False, context_weight=0.5)

    base = embedder.embed("Invoice payment delayed")
    with_context = embedder.embed("Invoice payment delayed", context=["finance"])

    assert base != with_context


def test_simple_text_categorizer_matches_keywords() -> None:
    categorizer = SimpleTextCategorizer(
        {
            "support": ("ticket", "bug"),
            "sales": ("deal", "prospect"),
        }
    )

    result = categorizer.categorize(
        "Investigating support ticket", context=["critical bug reported"]
    )

    assert result["category"] == "support"
    assert math.isclose(result["confidence"], 1.0)
    assert result["scores"]["support"] == 1.0


def test_text_embedding_comparer_combines_features() -> None:
    comparer = TextEmbeddingComparer(embedder=HashingTextEmbedder(dimension=64))

    summary = comparer.compare(
        "Customer raised a critical support ticket",
        "Critical ticket received from customer support",
    )

    assert summary["category_a"]["category"] == "support"
    assert summary["category_b"]["category"] == "support"
    assert summary["similarity"] > 0.6
