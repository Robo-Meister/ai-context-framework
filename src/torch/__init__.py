"""A lightweight stub implementation of the :mod:`torch` API used in tests.

This module provides just enough functionality for the unit tests in this
kata.  It implements a minimal subset of tensors, modules, serialization and
the ONNX exporter used by the code under test.  The goal is to avoid taking a
heavy dependency on the real PyTorch package whilst keeping the public API the
production code expects.

The implementation intentionally keeps the surface area tiny – only the
features exercised by the tests are supported.  The real project would rely on
the actual PyTorch package instead of this stub.
"""

from __future__ import annotations

from contextlib import contextmanager
import copy
import os
import pickle
import random
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Sequence
import types
import sys


class Tensor:
    """Very small tensor implementation backed by nested Python lists."""

    def __init__(self, data: Sequence[float] | Sequence[Sequence[float]]):
        self.data = _deep_copy(data)

    def clone(self) -> "Tensor":
        return Tensor(_deep_copy(self.data))

    def fill_(self, value: float) -> "Tensor":
        _fill_in_place(self.data, value)
        return self

    def __iter__(self) -> Iterator:
        return iter(self.data)


class Parameter(Tensor):
    """Represents a learnable parameter on a :class:`Module`."""


def _deep_copy(obj: Any) -> Any:
    if isinstance(obj, list):
        return [_deep_copy(item) for item in obj]
    return copy.deepcopy(obj)


def _fill_in_place(target: Any, value: float) -> None:
    if isinstance(target, list):
        for idx, item in enumerate(target):
            if isinstance(item, list):
                _fill_in_place(item, value)
            else:
                target[idx] = value


class Module:
    """Minimal version of :class:`torch.nn.Module`."""

    def __init__(self) -> None:
        object.__setattr__(self, "_parameters", {})
        object.__setattr__(self, "_modules", {})

    def __setattr__(self, name: str, value: Any) -> None:  # pragma: no cover - helper
        if isinstance(value, Parameter):
            self._parameters[name] = value
        elif isinstance(value, Module):
            self._modules[name] = value
        object.__setattr__(self, name, value)

    # The following attributes are populated in ``__setattr__``.
    _parameters: Dict[str, Parameter]
    _modules: Dict[str, "Module"]

    def parameters(self) -> Iterable[Parameter]:
        for param in self._parameters.values():
            yield param
        for module in self._modules.values():
            yield from module.parameters()

    def state_dict(self) -> Dict[str, Any]:
        state = {name: _deep_copy(param.data) for name, param in self._parameters.items()}
        for name, module in self._modules.items():
            state[name] = module.state_dict()
        return state

    def load_state_dict(self, state: Dict[str, Any]) -> None:
        for name, param in self._parameters.items():
            if name in state:
                param.data = _deep_copy(state[name])
        for name, module in self._modules.items():
            if name in state:
                module.load_state_dict(state[name])


class Linear(Module):
    def __init__(self, in_features: int, out_features: int) -> None:
        super().__init__()
        weight = Parameter([[0.0 for _ in range(in_features)] for _ in range(out_features)])
        bias = Parameter([0.0 for _ in range(out_features)])
        self.weight = weight
        self.bias = bias

    def forward(self, inputs: Tensor) -> Tensor:  # pragma: no cover - not used in tests
        if not isinstance(inputs, Tensor):
            raise TypeError("inputs must be a Tensor")
        result: List[List[float]] = []
        for row in inputs.data:  # type: ignore[attr-defined]
            out_row: List[float] = []
            for weights, bias in zip(self.weight.data, self.bias.data):
                total = sum(x * w for x, w in zip(row, weights)) + bias
                out_row.append(total)
            result.append(out_row)
        return Tensor(result)


def randn(*shape: int) -> Tensor:
    data: Any = _generate_random_data(list(shape))
    return Tensor(data)


def _generate_random_data(shape: List[int]) -> Any:
    if not shape:
        return random.random()
    size = shape[0]
    remainder = shape[1:]
    return [_generate_random_data(remainder) for _ in range(size)]


def no_grad():
    @contextmanager
    def _ctx():
        yield

    return _ctx()


def equal(left: Parameter | Tensor, right: Parameter | Tensor) -> bool:
    return left.data == right.data


def save(obj: Any, file: os.PathLike[str] | str) -> None:
    path = Path(file)
    with open(path, "wb") as fh:
        pickle.dump(obj, fh)


def load(file: os.PathLike[str] | str, map_location: str | None = None) -> Any:  # pragma: no cover - trivial
    path = Path(file)
    with open(path, "rb") as fh:
        return pickle.load(fh)


class _OnnxModule(types.ModuleType):
    def export(self, model: Module, example_input: Any, file: os.PathLike[str] | str) -> None:
        Path(file).write_bytes(b"ONNX model placeholder")


class _OptimModule(types.ModuleType):
    class Optimizer:  # pragma: no cover - not used directly
        def __init__(self, params: Iterable[Parameter], lr: float = 0.01) -> None:
            self.params = list(params)
            self.lr = lr

        def step(self) -> None:
            pass

        def zero_grad(self) -> None:
            pass


def _create_nn_module() -> types.ModuleType:
    module = types.ModuleType("torch.nn")
    module.Module = Module
    module.Linear = Linear
    module.Parameter = Parameter
    return module


nn = _create_nn_module()
onnx = _OnnxModule("torch.onnx")
optim = _OptimModule("torch.optim")

sys.modules[__name__ + ".nn"] = nn
sys.modules[__name__ + ".onnx"] = onnx
sys.modules[__name__ + ".optim"] = optim


__all__ = [
    "Tensor",
    "Parameter",
    "Module",
    "Linear",
    "randn",
    "no_grad",
    "equal",
    "save",
    "load",
    "nn",
    "onnx",
    "optim",
]
