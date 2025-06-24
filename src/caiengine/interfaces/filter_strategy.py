from typing import Any
import numpy as np


class FilterStrategy:
    def apply(self, data: Any) -> Any:
        """Apply filter to data and return the filtered result."""
        raise NotImplementedError()
