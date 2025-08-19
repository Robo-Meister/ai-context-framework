from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ModelManifest:
    """Manifest describing a portable model bundle."""

    model_name: str
    version: str
    training_context: Optional[str] = None
    preprocessing: List[str] = field(default_factory=list)
    postprocessing: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    license: Optional[str] = None
