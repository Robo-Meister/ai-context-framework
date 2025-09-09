from __future__ import annotations

import re
from typing import Dict, List


class IntentClassifier:
    """Naive rule-based intent classifier with funnel stage mapping.

    The classifier splits a message into segments and assigns each
    segment an intent and marketing funnel stage.
    """

    QUESTION_KEYWORDS = ["what", "how", "why", "when", "where", "who"]
    PURCHASE_KEYWORDS = ["buy", "purchase", "order", "price", "cost", "subscribe", "sign up"]
    SUPPORT_KEYWORDS = ["issue", "problem", "help", "support", "refund", "return"]
    OBJECTION_KEYWORDS = ["don't", "not", "can't", "won't", "expensive", "concern"]

    def segment(self, message: str) -> List[str]:
        """Split ``message`` into sentence-like segments."""
        parts = re.split(r"[.!?]", message)
        return [p.strip() for p in parts if p.strip()]

    def classify_segment(self, segment: str) -> Dict[str, str]:
        """Classify a single ``segment`` and tag with funnel stage."""
        lower = segment.lower()
        if any(k in lower for k in self.SUPPORT_KEYWORDS):
            intent = "support"
            stage = "retention"
        elif any(k in lower for k in self.QUESTION_KEYWORDS) or segment.strip().endswith("?"):
            intent = "question"
            stage = "awareness"
        elif any(k in lower for k in self.PURCHASE_KEYWORDS):
            intent = "purchase"
            stage = "conversion"
        elif any(k in lower for k in self.OBJECTION_KEYWORDS):
            intent = "objection"
            stage = "consideration"
        else:
            intent = "statement"
            stage = "awareness"
        return {"segment": segment, "intent": intent, "funnel_stage": stage}

    def parse(self, message: str) -> List[Dict[str, str]]:
        """Parse ``message`` into classified segments."""
        segments = self.segment(message)
        return [self.classify_segment(seg) for seg in segments]
