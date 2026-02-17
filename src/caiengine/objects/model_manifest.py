from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelManifest:
    """Manifest describing a portable model bundle."""

    model_name: str
    version: str
    schema_version: str = "1.0"
    engine_version: Optional[str] = None
    task: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    training_context: Optional[str] = None
    preprocessing: List[str] = field(default_factory=list)
    postprocessing: List[str] = field(default_factory=list)
    dependencies: Dict[str, str] = field(default_factory=dict)
    license: Optional[str] = None
