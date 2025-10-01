"""Minimal neural-style network built from :class:`ComplexLinear`."""

from __future__ import annotations

from typing import Iterable, List

from .complex_linear import ComplexLinear


class ComplexNet:
    """Stack of two :class:`ComplexLinear` layers with a ReLU activation."""

    def __init__(self, input_size: int, hidden_size: int, output_size: int):
        self.fc1 = ComplexLinear(input_size, hidden_size)
        self.fc2 = ComplexLinear(hidden_size, output_size)

    def forward(self, values: Iterable[float]) -> List[float]:
        hidden = [max(0.0, v) for v in self.fc1(values)]
        return self.fc2(hidden)

    __call__ = forward

