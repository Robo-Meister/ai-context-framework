from __future__ import annotations

import importlib


def test_import_caiengine_exposes_version_and_pipeline():
    import caiengine

    assert isinstance(caiengine.__version__, str)
    pipeline_cls = caiengine.ContextPipeline
    assert pipeline_cls.__module__.startswith("caiengine.pipelines")


def test_from_import_resolves_via_lazy_loader():
    module = importlib.import_module("caiengine")
    from caiengine import ContextPipeline  # noqa: F401  # pylint: disable=unused-import

    assert hasattr(module, "ContextPipeline")
    assert module.ContextPipeline is ContextPipeline
