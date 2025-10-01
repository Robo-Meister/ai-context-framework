
"""Data object definitions used across the framework."""

from .context_data import ContextData, SubscriptionHandle
from .context_query import ContextQuery
from .fused_context import FusedContext
from .model_metadata import ModelMetadata
from .model_manifest import ModelManifest
from .ocr_metadata import OCRMetadata, OCRSpan

__all__ = [
    "ContextData",
    "SubscriptionHandle",
    "ContextQuery",
    "FusedContext",
    "ModelMetadata",
    "ModelManifest",
    "OCRMetadata",
    "OCRSpan",
]
