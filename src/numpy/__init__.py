"""Small subset of the NumPy API required for the unit tests.

The project only needs ``numpy.array`` and ``numpy.testing.assert_array_equal``
for the test-suite.  Implementing them in pure Python avoids depending on the
full NumPy distribution, which is expensive to install in constrained
environments.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

__all__ = ["array", "testing", "isscalar", "asarray", "clip", "ndarray"]


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
        data = values.tolist()
    else:
        data = list(values)

    if dtype is not None:
        caster = _resolve_dtype(dtype)
        data = [caster(v) for v in data]

    return _Array(data)


def asarray(values: Iterable[float], dtype=None) -> _Array:  # noqa: D401 - minimal variant
    return array(values, dtype=dtype)


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


def clip(values, min_value, max_value, out=None):  # noqa: D401 - mimic numpy.clip behaviour
    scalar_input = not isinstance(values, (Iterable, _Array)) or isinstance(values, (str, bytes))

    lower = float(min_value) if min_value is not None else None
    upper = float(max_value) if max_value is not None else None

    def _clamp(value):
        result = float(value)
        if lower is not None and result < lower:
            result = lower
        if upper is not None and result > upper:
            result = upper
        return result

    if scalar_input:
        return _assign_out(out, _clamp(values), scalar_input=True)

    coerced = _coerce_sequence(values)
    result = [_clamp(v) for v in coerced]
    return _assign_out(out, result)


def isscalar(value) -> bool:  # pragma: no cover - simple helper
    return isinstance(value, (int, float))


def _resolve_dtype(dtype):
    if dtype in (None, float):
        return float
    if dtype in (int,):
        return int
    if isinstance(dtype, str):
        lowered = dtype.lower()
        if lowered.startswith("int"):
            return int
        if lowered.startswith("float"):
            return float
    raise TypeError(f"Unsupported dtype {dtype!r} for lightweight numpy stub")


ndarray = _Array


def _assign_out(out, data, *, scalar_input: bool = False):
    if out is None:
        if scalar_input:
            return data
        return _Array(data)

    if isinstance(out, _Array):
        if scalar_input:
            out._data = [data]
        else:
            out._data = list(data)
        return out

    if isinstance(out, list):  # simple container support for tests
        if scalar_input:
            if out:
                out[0] = data
            else:
                out.append(data)
        else:
            out[:] = list(data)
        return out

    raise TypeError("Unsupported output container for lightweight numpy stub")
