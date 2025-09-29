from __future__ import annotations

from typing import List, Dict, Optional

from caiengine.parser.intent_classifier import IntentClassifier


class IntentPipeline:
    """Pipeline wrapper around :class:`IntentClassifier`.

    This pipeline can be optionally inserted into a workflow to
    extract intents and funnel stages from a free-form message.
    """

    def __init__(self, classifier: Optional[IntentClassifier] = None) -> None:
        self.classifier = classifier or IntentClassifier()

    def process(self, message: str) -> List[Dict[str, str]]:
        """Return intent classifications for ``message``."""
        return self.classifier.parse(message)
