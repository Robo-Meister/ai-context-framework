"""Minimal PyTorch compatibility layer for the test suite."""

from __future__ import annotations

import json
import random
import sys
import types
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Sequence

__all__ = [
    "Tensor",
    "nn",
    "onnx",
    "optim",
    "randn",
    "save",
    "load",
    "no_grad",
    "equal",
]


def _deep_copy(value):
    if isinstance(value, list):
        return [_deep_copy(v) for v in value]
    return value


class Tensor:
    """Lightweight tensor holding nested lists."""

    def __init__(self, data: Sequence):
        self._data = self._to_nested_list(data)

    def tolist(self) -> List:
        return _deep_copy(self._data)

    def __iter__(self) -> Iterator:
        return iter(self._data)

    def item(self):  # pragma: no cover - convenience helper
        if isinstance(self._data, list) and len(self._data) == 1:
            return self._data[0]
        raise ValueError("Tensor does not contain a single value")

    @staticmethod
    def _to_nested_list(data):
        if isinstance(data, Tensor):
            return data.tolist()
        if isinstance(data, (list, tuple)):
            return [Tensor._to_nested_list(v) for v in data]
        return float(data)


def randn(*size: int) -> Tensor:
    if not size:
        raise ValueError("randn expects at least one dimension")
    return Tensor(_random_nested_list(list(size)))


def _random_nested_list(shape: List[int]):
    if len(shape) == 1:
        return [random.gauss(0.0, 1.0) for _ in range(shape[0])]
    return [_random_nested_list(shape[1:]) for _ in range(shape[0])]


class Parameter:
    """Simple parameter object supporting in-place updates."""

    def __init__(self, data):
        self.data = _deep_copy(data)

    def fill_(self, value: float) -> "Parameter":
        def _fill(target):
            if isinstance(target, list):
                return [_fill(v) for v in target]
            return float(value)

        self.data = _fill(self.data)
        return self

    def tolist(self) -> List:
        return _deep_copy(self.data)

    def __iter__(self):  # pragma: no cover - helper
        if isinstance(self.data, list):
            return iter(self.data)
        return iter([self.data])


class Module:
    """Subset of ``torch.nn.Module`` providing parameter management."""

    def __init__(self) -> None:
        object.__setattr__(self, "_parameters", {})
        object.__setattr__(self, "_modules", {})
        self.training = True

    def __setattr__(self, name, value):
        if isinstance(value, Parameter):
            self._parameters[name] = value
        elif isinstance(value, Module):
            self._modules[name] = value
        object.__setattr__(self, name, value)

    def parameters(self):
        for param in self._parameters.values():
            yield param
        for module in self._modules.values():
            yield from module.parameters()

    def state_dict(self, prefix: str = "") -> Dict[str, List]:
        state: Dict[str, List] = {}
        for name, param in self._parameters.items():
            state[f"{prefix}{name}"] = param.tolist()
        for name, module in self._modules.items():
            state.update(module.state_dict(f"{prefix}{name}."))
        return state

    def load_state_dict(self, state: Dict[str, Sequence]) -> None:
        for name, values in state.items():
            parts = name.split(".")
            target = self
            for part in parts[:-1]:
                target = target._modules[part]
            param_name = parts[-1]
            if param_name in target._parameters:
                target._parameters[param_name].data = _deep_copy(values)

    def forward(self, *args, **kwargs):  # pragma: no cover - override in subclasses
        raise NotImplementedError

    def __call__(self, *args, **kwargs):  # pragma: no cover - not used in tests
        return self.forward(*args, **kwargs)


class Linear(Module):
    def __init__(self, in_features: int, out_features: int) -> None:
        super().__init__()
        weight = [[0.0 for _ in range(in_features)] for _ in range(out_features)]
        bias = [0.0 for _ in range(out_features)]
        self.weight = Parameter(weight)
        self.bias = Parameter(bias)


class _NNNamespace(types.ModuleType):
    def __init__(self):
        super().__init__("torch.nn")
        self.Module = Module
        self.Linear = Linear

        class MSELoss:
            def __call__(self, prediction, target):
                pred = prediction if isinstance(prediction, (int, float)) else prediction[0]
                targ = target if isinstance(target, (int, float)) else target[0]
                diff = float(pred) - float(targ)
                return diff * diff

        self.MSELoss = MSELoss

        def ParameterFactory(data):
            return Parameter(data)

        self.Parameter = ParameterFactory


nn = _NNNamespace()


class _Optimizer:
    def __init__(self, parameters, lr: float = 0.01):
        self.parameters = list(parameters)
        self.lr = lr

    def zero_grad(self):  # pragma: no cover - compatibility no-op
        return None

    def step(self):  # pragma: no cover - compatibility no-op
        return None


class _OptimNamespace(types.ModuleType):
    def __init__(self):
        super().__init__("torch.optim")

        class Adam(_Optimizer):
            pass

        self.Adam = Adam


optim = _OptimNamespace()


def no_grad():
    class _NoGrad:
        def __enter__(self, *args):  # pragma: no cover - trivial
            return self

        def __exit__(self, exc_type, exc, tb):  # pragma: no cover - trivial
            return False

    return _NoGrad()


def equal(a, b) -> bool:
    return _coerce_to_list(a) == _coerce_to_list(b)


def _coerce_to_list(value):
    if isinstance(value, Parameter):
        return value.tolist()
    if isinstance(value, Tensor):
        return value.tolist()
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return [_coerce_to_list(v) for v in value]
    return float(value)


def save(obj, path):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle)


def load(path, map_location=None):  # noqa: D401 - mimic torch.load signature
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# torch.onnx namespace -------------------------------------------------------

onnx = types.ModuleType("torch.onnx")


def _export(model: Module, example_input: Tensor, file_path, *args, **kwargs) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("Stub ONNX model for " + model.__class__.__name__)


onnx.export = _export


sys.modules.setdefault("torch.nn", nn)
sys.modules.setdefault("torch.optim", optim)
sys.modules.setdefault("torch.onnx", onnx)

# expose namespace objects

