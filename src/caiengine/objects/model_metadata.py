from dataclasses import dataclass
from typing import List


@dataclass
class ModelMetadata:
    """Metadata describing a persisted model."""

    model_name: str
    version: str
    supported_context_types: List[str]
    training_hash: str
