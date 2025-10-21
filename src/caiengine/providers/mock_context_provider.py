import logging
from datetime import datetime, timedelta
from typing import List


class MockContextProvider:
    def __init__(self) -> None:
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def get_context(self) -> List[dict]:
        base = datetime(2025, 5, 21, 9, 0)
        contexts = [
            {
                "id": 1,
                "roles": ["editor"],
                "timestamp": base,
                "situations": ["deal1"],
                "content": "Edit made to deal1",
                "context": {"deal": "1"},
                "confidence": 0.9
            },
            {
                "id": 2,
                "roles": ["editor"],
                "timestamp": base + timedelta(minutes=2),
                "situations": ["deal1"],
                "content": "Edit again on deal1",
                "context": {"deal": "1"},
                "confidence": 0.85
            },
            {
                "id": 3,
                "roles": ["viewer"],
                "timestamp": base + timedelta(hours=1),
                "situations": ["deal2"],
                "content": "View of deal2",
                "context": {"deal": "2"},
                "confidence": 0.95
            }
        ]
        if not hasattr(self, "logger"):
            self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self.logger.debug("Returning mock context entries", extra={"count": len(contexts)})
        return contexts
