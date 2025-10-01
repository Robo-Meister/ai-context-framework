"""Small subset of the NumPy API required for the unit tests.

The project only needs ``numpy.array`` and ``numpy.testing.assert_array_equal``
for the test-suite.  Implementing them in pure Python avoids depending on the
full NumPy distribution, which is expensive to install in constrained
environments.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

__all__ = ["array", "testing", "isscalar"]


bool_ = bool  # pragma: no cover - compatibility alias


class _Array:
    """Lightweight array wrapper providing sequence behaviour."""

    def __init__(self, values: Sequence[float]):
        self._data = [float(v) for v in values]

    def __iter__(self):  # pragma: no cover - simple delegation
        return iter(self._data)

    def __len__(self) -> int:  # pragma: no cover - simple delegation
        return len(self._data)

    def __getitem__(self, item):  # pragma: no cover - simple delegation
        return self._data[item]

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"array({self._data!r})"

    def tolist(self) -> List[float]:  # pragma: no cover - convenience helper
        return list(self._data)


def array(values: Iterable[float], dtype=None) -> _Array:  # noqa: D401 - matches numpy signature
    """Create a small wrapper mimicking ``numpy.array``."""

    if isinstance(values, _Array):
        return _Array(values.tolist())
    return _Array(list(values))


class _TestingModule:
    """Subset of :mod:`numpy.testing` used in tests."""

    @staticmethod
    def assert_array_equal(actual, expected) -> None:
        act_list = _coerce_sequence(actual)
        exp_list = _coerce_sequence(expected)
        if act_list != exp_list:
            raise AssertionError(f"Arrays are not equal: {act_list!r} != {exp_list!r}")


def _coerce_sequence(value) -> List[float]:
    if isinstance(value, _Array):
        return value.tolist()
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return [float(v) for v in value]
    return [float(value)]


testing = _TestingModule()

def isscalar(value) -> bool:  # pragma: no cover - simple helper
    return isinstance(value, (int, float))
