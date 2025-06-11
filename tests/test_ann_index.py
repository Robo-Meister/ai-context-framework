from core.ann_index import ANNIndex


def test_ann_index_basic():
    idx = ANNIndex(vector_dim=3)
    idx.add_item("a", [1.0, 0.0, 0.0])
    idx.add_item("b", [0.0, 1.0, 0.0])
    idx.build()
    result = idx.query([0.9, 0.1, 0.0], k=1)
    assert result[0] == "a"
