import json
from typing import Any, Dict, List, Union

class RoboConnectorNormalizer:
    """Normalize Robo Connector workflow logs into a common schema."""

    DEFAULT_STEP_FIELDS = {
        "name": "",
        "action": "",
        "description": "",
        "group": "",
        "decorators": [],
        "level": 0,
        "optional": False,
        "changeable": False,
        "cancelable": False,
        "required_manual": False,
        "possible_ai": False,
        "possible_service": False,
        "possible_manual": False,
        "possible_robots": False,
        "input_fields": [],
        "output_fields": [],
        "next": None,
        "risks": [],
    }

    def _normalize_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(self.DEFAULT_STEP_FIELDS)
        for key, value in step.items():
            normalized[key] = value
        return normalized

    def normalize(self, data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Return normalized workflow dictionary."""
        if isinstance(data, str):
            data = json.loads(data)

        result: Dict[str, Any] = {
            "name": data.get("workflow_name") or data.get("name", ""),
            "description": data.get("description", ""),
            "category": data.get("category"),
            "fields": data.get("fields", []),
            "steps": [],
        }

        for step in data.get("steps", []):
            result["steps"].append(self._normalize_step(step))
        if "need_project" in data or "need_client" in data or "need_payment" in data:
            result["requirements"] = {
                "need_project": data.get("need_project", False),
                "need_client": data.get("need_client", False),
                "need_payment": data.get("need_payment", False),
            }
        return result
