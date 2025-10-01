"""Lightweight linear helper used by the learning components.

The original project relied on PyTorch layers.  To keep the test environment
dependency-free we emulate the behaviour with plain Python lists.  The helper
performs a dense matrix multiplication followed by bias addition and exposes
just enough surface area for higher level abstractions.
"""

from __future__ import annotations

from typing import Iterable, List


class ComplexLinear:
    """Simple dense linear transform using Python lists."""

    def __init__(self, in_features: int, out_features: int):
        self.in_features = in_features
        self.out_features = out_features
        self.weights = [[0.0 for _ in range(in_features)] for _ in range(out_features)]
        self.bias = [0.0 for _ in range(out_features)]

    def __call__(self, inputs: Iterable[float]) -> List[float]:
        data = list(float(x) for x in inputs)
        return [
            sum(weight * value for weight, value in zip(row, data)) + bias
            for row, bias in zip(self.weights, self.bias)
        ]

