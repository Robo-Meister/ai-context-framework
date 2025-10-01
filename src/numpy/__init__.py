"""A minimal stub of :mod:`numpy` providing helpers required by the tests."""

from __future__ import annotations

from typing import Iterable, List
import types
import sys


class ndarray(list):
    """Simple list backed array used for comparisons in tests."""

    def __init__(self, values: Iterable[float]):
        super().__init__(float(v) for v in values)

    def __array__(self):  # pragma: no cover - compatibility hook
        return list(self)


def array(values: Iterable[float]) -> ndarray:
    if isinstance(values, ndarray):
        return ndarray(values)
    if isinstance(values, list):
        return ndarray(values)
    return ndarray(list(values))


def _assert_array_equal(left: Iterable[float], right: Iterable[float]) -> None:
    left_list: List[float] = list(left)
    right_list: List[float] = list(right)
    if left_list != right_list:
        raise AssertionError(f"Arrays are not equal: {left_list!r} != {right_list!r}")


testing = types.SimpleNamespace(assert_array_equal=_assert_array_equal)

sys.modules[__name__ + ".testing"] = testing


def isscalar(value: object) -> bool:
    return not isinstance(value, (list, tuple, ndarray))


bool_ = bool


__all__ = ["ndarray", "array", "testing", "isscalar", "bool_"]
