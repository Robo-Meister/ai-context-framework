import os

import pytest

os.environ.setdefault("CAIENGINE_LIGHT_IMPORT", "1")

pytest.importorskip("torch")

from caiengine.core.categorizer import NeuralEmbeddingCategorizer


@pytest.fixture()
def embedding_categorizer() -> NeuralEmbeddingCategorizer:
    return NeuralEmbeddingCategorizer(
        {
            "sales": (
                "Closing a high value deal with an enterprise prospect",
                "Following up with a promising pipeline opportunity",
            ),
            "support": (
                "Resolving a customer ticket with a serious outage",
                "Investigating a bug report escalated by support",
            ),
        }
    )


def test_sales_item_scores_highest(embedding_categorizer: NeuralEmbeddingCategorizer) -> None:
    item = {
        "content": "Meeting with the sales team to close a new prospect deal",
        "tags": ["pipeline", "deal"],
    }

    result = embedding_categorizer.categorize(item)

    assert result["category"] == "sales"
    assert set(result["scores"]) == {"sales", "support"}
    assert pytest.approx(sum(result["scores"].values()), rel=1e-6) == 1.0


def test_support_item_scores_highest(
    embedding_categorizer: NeuralEmbeddingCategorizer,
) -> None:
    item = {
        "content": "Working through an urgent customer ticket about an outage",
        "keywords": ["ticket", "outage"],
    }

    result = embedding_categorizer.categorize(item)

    assert result["category"] == "support"
    assert result["scores"]["support"] > result["scores"]["sales"]


def test_unknown_category_when_no_text(
    embedding_categorizer: NeuralEmbeddingCategorizer,
) -> None:
    result = embedding_categorizer.categorize({})

    assert result["category"] == embedding_categorizer.unknown_category
    assert result["confidence"] == 0.0
    assert result["scores"] == {}
