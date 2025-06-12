class ContextProvider:
    """Basic context provider with trust calculation support.

    The ``context_weights`` structure can contain nested dictionaries to
    represent sublayers (e.g. ``{"environment": {"camera": 0.1, "temperature":
    0.08}}``).  This allows callers to provide fine grained context while still
    falling back to sensible defaults.
    """

    def __init__(self, context_weights: dict | None = None, layer_types: dict | None = None):
        # Default weights sum to 1.0
        self.context_weights = context_weights or {
            "role": 0.18,
            "environment": {
                "camera": 0.09,
                "temperature": 0.09,
            },
            "network": 0.12,
            "input": 0.12,
            "timeframe": 0.1,
            "mood": 0.08,
            "label": 0.1,  # Optional but powerful
            "device": 0.06,
            "location": 0.06,
        }

        # Optional mapping of layer name (or ``layer.sublayer``) to a data type
        # string.  Not used directly in this class but allows downstream
        # components to pick appropriate filters/deduplicators.
        self.layer_types = layer_types or {}

    def _iter_weights(self, weights: dict | None = None, prefix: str = ""):
        if weights is None:
            weights = self.context_weights
        for layer, weight in weights.items():
            if isinstance(weight, dict):
                yield from self._iter_weights(weight, prefix + layer + ".")
            else:
                yield prefix + layer, weight

    def calculate_trust(self, context_data: dict) -> float:
        """Calculate trust score for provided context data.

        Nested sublayers are handled using dot notation. Missing layers simply
        contribute ``0`` to the final score.
        """

        weights = list(self._iter_weights())
        total_weight = sum(w for _, w in weights)
        present_sum = 0.0

        for key, weight in weights:
            if "." in key:
                layer, sub = key.split(".", 1)
                presence = 1 if context_data.get(layer, {}).get(sub) else 0
            else:
                presence = 1 if context_data.get(key) else 0
            present_sum += weight * presence

        return present_sum / total_weight if total_weight else 0.0

    def get_adjusted_weight(self, base_weight: float, context_data: dict) -> float:
        """Return weight scaled by calculated trust."""
        trust_score = self.calculate_trust(context_data)
        return base_weight * trust_score
