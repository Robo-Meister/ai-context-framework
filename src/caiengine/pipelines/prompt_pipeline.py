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
from caiengine.common import AuditLogger


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
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.provider = context_provider
        self.engine = inference_engine
        self.parser = PromptParser()
        self.encoder = ContextEncoder()
        self.comparer = VectorComparer()
        self.fuser = Fuser()
        self.feedback_loop = feedback_loop
        self.top_k = top_k
        self.audit_logger = audit_logger

    def process(self, prompt: str, query: ContextQuery) -> Dict[str, any]:
        """Process ``prompt`` against stored context and return the inference result."""
        if self.audit_logger:
            self.audit_logger.log("PromptPipeline", "run_start", {})

        parsed = self.parser.transform(prompt)
        if self.audit_logger:
            self.audit_logger.log("PromptPipeline", "parsed", {})

        vec = self.encoder.encode(parsed)
        parsed["vector"] = vec
        if self.audit_logger:
            self.audit_logger.log("PromptPipeline", "encoded", {})

        all_ctx = self.provider.get_context(query)
        if self.audit_logger:
            self.audit_logger.log("PromptPipeline", "context_retrieved", {"count": len(all_ctx)})

        scored: List[Dict] = []
        for item in all_ctx:
            vec2 = item.get("vector")
            if vec2 is None:
                vec2 = self.encoder.encode(item.get("context", {}))
            score = self.comparer.cosine_similarity(vec, vec2)
            scored.append({"item": item, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_items = [s["item"] for s in scored[: self.top_k]]
        if self.audit_logger:
            self.audit_logger.log("PromptPipeline", "scored", {"top_k": len(top_items)})

        fused = self.fuser.fuse({("prompt", "", ""): top_items})
        if self.audit_logger:
            self.audit_logger.log("PromptPipeline", "fused", {"result_count": len(fused)})

        result = self.engine.predict({"prompt": prompt, "context": fused})
        if self.audit_logger:
            self.audit_logger.log("PromptPipeline", "predicted", {})

        if self.feedback_loop:
            suggestions = self.feedback_loop.suggest([], [result])
            if suggestions:
                result = suggestions[0]
            if self.audit_logger:
                self.audit_logger.log("PromptPipeline", "feedback_applied", {})
        return {"result": result, "parsed": parsed, "fused": fused}
