from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from caiengine.core.vector_normalizer.context_encoder import ContextEncoder


class PromptParser:
    """Very simple keyword-based parser that extracts context features from a text prompt.

    The parser looks for known keywords related to time, location, role, label and mood and
    maps them to the vocabulary expected by :class:`ContextEncoder`.
    """

    TIME_KEYWORDS = ["morning", "afternoon", "evening", "night", "before lunch"]
    SPACE_KEYWORDS = {
        "around the house": ["home", "house", "kitchen", "garden"],
        "at office": ["office", "work", "desk"],
        "warehouse": ["warehouse", "storage"],
    }
    ROLE_KEYWORDS = {
        "admin": ["admin", "administrator", "root"],
        "user": ["user", "client", "customer"],
        "guest": ["guest", "visitor"],
    }
    LABEL_KEYWORDS = {
        "invoice": ["invoice", "bill"],
        "task": ["task", "todo"],
        "report": ["report"],
    }
    MOOD_KEYWORDS = {
        "happy": ["happy", "glad"],
        "neutral": ["ok", "fine", "neutral"],
        "stressed": ["stressed", "anxious", "worried"],
    }

    def _match_keyword(self, text: str, mapping: Dict[str, Any]) -> Optional[str]:
        lower = text.lower()
        for key, keywords in mapping.items():
            if isinstance(keywords, list):
                if any(kw in lower for kw in keywords):
                    return key
            else:  # when mapping is list
                if key in lower:
                    return key
        return None

    def _match_list(self, text: str, keywords: list[str]) -> Optional[str]:
        lower = text.lower()
        for kw in keywords:
            if kw in lower:
                return kw
        return None

    def transform(self, prompt: str) -> Dict[str, Any]:
        """Transform ``prompt`` into a context dictionary."""
        context: Dict[str, Any] = {
            "time": self._match_list(prompt, self.TIME_KEYWORDS),
            "space": self._match_keyword(prompt, self.SPACE_KEYWORDS),
            "role": self._match_keyword(prompt, self.ROLE_KEYWORDS),
            "label": self._match_keyword(prompt, self.LABEL_KEYWORDS),
            "mood": self._match_keyword(prompt, self.MOOD_KEYWORDS),
            "content": prompt,
            "network": None,
        }
        return context

    def parse_to_matrix(self, prompt: str) -> Tuple[Dict[str, Any], list]:
        """Return context categories and their encoded matrix for ``prompt``.

        The method first parses the natural language ``prompt`` into a context
        dictionary using :meth:`transform`. The resulting dictionary is then
        encoded into a numeric vector (context matrix) by
        :class:`ContextEncoder`.

        :param prompt: Natural language text describing a situation.
        :return: Tuple of ``(context_dict, context_matrix)``.
        """

        context = self.transform(prompt)
        encoder = ContextEncoder()
        matrix = encoder.encode(context)
        return context, matrix
