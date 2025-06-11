import json
import os
import uuid
from typing import Optional, List
from datetime import datetime
from objects.context_data import ContextData
from objects.context_query import ContextQuery
from .base_context_provider import BaseContextProvider

class FileBasedContextProvider(BaseContextProvider):
    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path

    def fetch_context(self, query_params: ContextQuery) -> List[ContextData]:
        results = []
        for filename in os.listdir(self.folder_path):
            if filename.endswith(".json"):
                with open(os.path.join(self.folder_path, filename)) as f:
                    entries = json.load(f)
                    for entry in entries:
                        ts = datetime.fromisoformat(entry["timestamp"])
                        if query_params.time_range[0] <= ts <= query_params.time_range[1]:
                            results.append(ContextData(
                                payload=entry["data"],
                                timestamp=ts,
                                source_id=entry.get("source_id", "file"),
                                confidence=entry.get("confidence", 1.0),
                                metadata=entry.get("metadata", {})
                            ))
        return results
    def get_context(self, query: ContextQuery = None) -> List[dict]:
        raw_contexts = self.fetch_context(query)
        return [self._to_dict(cd) for cd in raw_contexts]

    def _to_dict(self, cd: ContextData) -> dict:
        return {
            "id": cd.metadata.get("id", None),
            "roles": cd.metadata.get("roles", []),
            "timestamp": cd.timestamp,
            "situations": cd.metadata.get("situations", []),
            "content": cd.metadata.get("content", ""),
            "context": cd.payload,
            "confidence": cd.confidence,
        }
    def publish_context(self, data: ContextData):
        """Broadcast file-based context data to subscribers and peers."""
        super().publish_context(data)

# provider = FileBasedContextProvider("./log_folder")
#
# # Fetching context
# query = ContextQuery(
#     roles=["operator"],
#     time_range=(datetime(2025, 5, 1), datetime(2025, 5, 21)),
#     scope="production",
#     data_type="event"
# )
# context_data = provider.fetch_context(query)
#
# # Subscribing to live data
# def on_data(data: ContextData):
#     print(f"New context arrived: {data}")
#
# subscription_id = provider.subscribe_context(on_data)
#
# # Simulate push (in real case: from Redis, Kafka, etc.)
# provider.publish_context(ContextData(
#     payload={"action": "sensor_trigger", "value": 77},
#     timestamp=datetime.utcnow(),
#     source_id="sensor:123",
#     confidence=0.95,
#     metadata={"unit": "Celsius"}
# ))
