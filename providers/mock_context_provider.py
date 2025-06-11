from datetime import datetime, timedelta
from typing import List


class MockContextProvider:
    def get_context(self) -> List[dict]:
        base = datetime(2025, 5, 21, 9, 0)
        return [
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
