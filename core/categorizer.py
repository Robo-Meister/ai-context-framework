from datetime import datetime
from ContextAi.interfaces.context_provider import ContextProvider

class Categorizer:
    def __init__(self, context_provider: ContextProvider):
        self.context_provider = context_provider

    def _get_time_bucket(self, dt: datetime) -> str:
        # Example bucket: "Mon_09" = Monday 9am hour
        weekday = dt.strftime('%a')  # Mon, Tue, Wed, ...
        hour = dt.hour
        return f"{weekday}_{hour:02d}"

    def categorize(self, input_item: dict, candidates: list[dict]) -> str:
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            match_score = self.compare_layers(input_item['context'], candidate['context'])
            adjusted_weight = self.context_provider.get_adjusted_weight(candidate['base_weight'], candidate['context'])
            total_score = match_score * adjusted_weight

            if total_score > best_score:
                best_score = total_score
                best_match = candidate['category']

        return best_match or "unknown"

    def compare_layers(self, ctx1: dict, ctx2: dict) -> float:
        matched_layers = sum(1 for k in ctx1 if ctx1.get(k) == ctx2.get(k))
        total_layers = len(set(ctx1.keys()) | set(ctx2.keys()))
        return matched_layers / total_layers if total_layers else 0.0

# Simple test example
if __name__ == "__main__":
    import pprint
    categorizer = Categorizer()

    # Sample data batch
    data = [
        {
            "id": 1,
            "roles": ["owner", "editor"],
            "timestamp": datetime(2025, 5, 21, 9, 15),
            "situations": ["projectA", "clientB"],
            "content": "Context about project A for client B"
        },
        {
            "id": 2,
            "roles": ["viewer"],
            "timestamp": datetime(2025, 5, 21, 9, 45),
            "situations": ["clientB"],
            "content": "Viewer access context for client B"
        },
        {
            "id": 3,
            "roles": ["owner"],
            "timestamp": datetime(2025, 5, 22, 14, 0),
            "situations": ["projectC"],
            "content": "Context for project C"
        },
    ]

    categorized_result = categorizer.categorize(data)
    pprint.pprint(dict(categorized_result))
