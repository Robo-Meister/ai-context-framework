from datetime import datetime
from caiengine.interfaces.context_provider import ContextProvider

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

    def _flatten(self, ctx: dict, prefix: str = "") -> dict:
        flat = {}
        for k, v in ctx.items():
            if isinstance(v, dict):
                flat.update(self._flatten(v, prefix + k + "."))
            else:
                flat[prefix + k] = v
        return flat

    def compare_layers(self, ctx1: dict, ctx2: dict) -> float:
        """Return ratio of matching context layers (supports sublayers)."""
        f1 = self._flatten(ctx1)
        f2 = self._flatten(ctx2)
        keys = set(f1.keys()) | set(f2.keys())
        if not keys:
            return 0.0
        matched = sum(1 for k in keys if f1.get(k) == f2.get(k))
        return matched / len(keys)

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
