from typing import Protocol, Callable, List, Optional
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from .ocr_metadata import OCRMetadata

@dataclass
class ContextData:
    payload: dict
    timestamp: datetime
    source_id: str
    metadata: dict
    roles: List[str]
    situations: List[str]
    content: any
    confidence: float = 1.0
    ocr_metadata: Optional[OCRMetadata] = None


SubscriptionHandle = UUID
