from __future__ import annotations

from typing import Dict, List, Optional

from caiengine.parser.prompt_parser import PromptParser
from caiengine.core.vector_normalizer.context_encoder import ContextEncoder
from caiengine.core.vector_normalizer.vector_comparer import VectorComparer
from caiengine.core.fuser import Fuser
from caiengine.interfaces.context_provider import ContextProvider
from caiengine.interfaces.inference_engine import AIInferenceEngine
from caiengine.objects.context_query import ContextQuery
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop


class PromptPipeline:
    """Pipeline that converts a text prompt into a context matrix and queries the provider.

    The prompt is first parsed into a structured context using :class:`PromptParser`.
    The resulting context dictionary is encoded as a vector (a "context matrix") which is
    compared against stored context entries. The most similar items are fused and passed to
    the supplied inference engine. Optionally a :class:`GoalDrivenFeedbackLoop` may adjust
    the final result.
    """

    def __init__(
        self,
        context_provider: ContextProvider,
        inference_engine: AIInferenceEngine,
        feedback_loop: Optional[GoalDrivenFeedbackLoop] = None,
        top_k: int = 3,
    ) -> None:
        self.provider = context_provider
        self.engine = inference_engine
        self.parser = PromptParser()
        self.encoder = ContextEncoder()
        self.comparer = VectorComparer()
        self.fuser = Fuser()
        self.feedback_loop = feedback_loop
        self.top_k = top_k

    def process(self, prompt: str, query: ContextQuery) -> Dict[str, any]:
        """Process ``prompt`` against stored context and return the inference result."""
        parsed = self.parser.transform(prompt)
        vec = self.encoder.encode(parsed)
        parsed["vector"] = vec

        all_ctx = self.provider.get_context(query)
        scored: List[Dict] = []
        for item in all_ctx:
            vec2 = item.get("vector")
            if vec2 is None:
                vec2 = self.encoder.encode(item.get("context", {}))
            score = self.comparer.cosine_similarity(vec, vec2)
            scored.append({"item": item, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_items = [s["item"] for s in scored[: self.top_k]]
        fused = self.fuser.fuse({("prompt", "", ""): top_items})
        result = self.engine.predict({"prompt": prompt, "context": fused})
        if self.feedback_loop:
            suggestions = self.feedback_loop.suggest([], [result])
            if suggestions:
                result = suggestions[0]
        return {"result": result, "parsed": parsed, "fused": fused}
