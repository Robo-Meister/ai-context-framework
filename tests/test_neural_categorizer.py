import os

os.environ.setdefault("CAIENGINE_LIGHT_IMPORT", "1")

import pytest

torch = pytest.importorskip("torch")

from caiengine.core.categorizer import NeuralKeywordCategorizer


@pytest.fixture()
def sample_categorizer() -> NeuralKeywordCategorizer:
    return NeuralKeywordCategorizer(
        {
            "sales": ("deal", "prospect"),
            "support": ("bug", "ticket"),
            "marketing": ("campaign", "brand"),
        }
    )


def test_categorize_from_content(sample_categorizer: NeuralKeywordCategorizer) -> None:
    item = {"content": "The prospect confirmed the deal details."}

    result = sample_categorizer.categorize(item)

    assert result["category"] == "sales"
    assert result["confidence"] > 0.5
    assert pytest.approx(result["scores"]["sales"], rel=1e-5) == result["confidence"]


def test_categorize_from_context(sample_categorizer: NeuralKeywordCategorizer) -> None:
    item = {
        "content": "Investigating customer complaint",
        "context": {"details": "Critical BUG reported by customer"},
    }

    result = sample_categorizer.categorize(item)

    assert result["category"] == "support"
    assert result["confidence"] > 0.5


def test_unknown_when_no_keywords(sample_categorizer: NeuralKeywordCategorizer) -> None:
    item = {"content": "Completely unrelated text"}

    result = sample_categorizer.categorize(item)

    assert result["category"] == sample_categorizer.unknown_category
    assert result["confidence"] == 0.0
    assert result["scores"] == {}
