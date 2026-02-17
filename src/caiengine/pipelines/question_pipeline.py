from typing import List, Dict, Optional

from caiengine.core.vector_normalizer.context_encoder import ContextEncoder
from caiengine.core.vector_normalizer.vector_comparer import VectorComparer
from caiengine.core.fuser import Fuser
from caiengine.interfaces.context_provider import ContextProvider
from caiengine.interfaces.inference_engine import InferenceEngineInterface
from caiengine.objects.context_query import ContextQuery
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop
from caiengine.common import AuditLogger


class QuestionPipeline:
    """Simple pipeline for question answering over stored context.

    The pipeline encodes the provided question context as a vector and
    compares it against context entries returned by ``context_provider``.
    The most similar items are fused and passed to ``inference_engine``.
    If a ``feedback_loop`` is supplied, its suggestions are applied to the
    engine result before returning.
    """

    def __init__(
        self,
        context_provider: ContextProvider,
        inference_engine: InferenceEngineInterface,
        feedback_loop: Optional[GoalDrivenFeedbackLoop] = None,
        top_k: int = 3,
        audit_logger: AuditLogger | None = None,
    ):
        self.provider = context_provider
        self.engine = inference_engine
        self.encoder = ContextEncoder()
        self.comparer = VectorComparer()
        self.fuser = Fuser()
        self.feedback_loop = feedback_loop
        self.top_k = top_k
        self.audit_logger = audit_logger

    def ask(self, question: str, query: ContextQuery, context: Optional[Dict] = None) -> Dict:
        """Return a suggested answer for ``question`` using optional ``context``."""
        if self.audit_logger:
            self.audit_logger.log("QuestionPipeline", "run_start", {})

        all_ctx = self.provider.get_context(query)
        q_features = context or {}
        q_vec = self.encoder.encode(q_features)
        if self.audit_logger:
            self.audit_logger.log("QuestionPipeline", "encoded", {})

        scored: List[Dict] = []
        for item in all_ctx:
            vec = item.get("vector")
            if vec is None:
                vec = self.encoder.encode(item.get("context", {}))
            score = self.comparer.cosine_similarity(q_vec, vec)
            scored.append({"item": item, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_items = [s["item"] for s in scored[: self.top_k]]
        if self.audit_logger:
            self.audit_logger.log("QuestionPipeline", "scored", {"top_k": len(top_items)})

        fused = self.fuser.fuse({("qa", "", ""): top_items})
        if self.audit_logger:
            self.audit_logger.log("QuestionPipeline", "fused", {"result_count": len(fused)})

        answer = self.engine.predict({"question": question, "context": fused})
        if self.audit_logger:
            self.audit_logger.log("QuestionPipeline", "predicted", {})

        if self.feedback_loop:
            suggestions = self.feedback_loop.suggest([], [answer])
            if suggestions:
                answer = suggestions[0]
            if self.audit_logger:
                self.audit_logger.log("QuestionPipeline", "feedback_applied", {})
        return {"answer": answer, "fused": fused}
