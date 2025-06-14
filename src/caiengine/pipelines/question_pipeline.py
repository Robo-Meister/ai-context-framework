from typing import List, Dict, Optional

from caiengine.core.vector_normalizer.context_encoder import ContextEncoder
from caiengine.core.vector_normalizer.vector_comparer import VectorComparer
from caiengine.core.fuser import Fuser
from caiengine.interfaces.context_provider import ContextProvider
from caiengine.interfaces.inference_engine import AIInferenceEngine
from caiengine.objects.context_query import ContextQuery
from caiengine.core.goal_feedback_loop import GoalDrivenFeedbackLoop


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
        inference_engine: AIInferenceEngine,
        feedback_loop: Optional[GoalDrivenFeedbackLoop] = None,
        top_k: int = 3,
    ):
        self.provider = context_provider
        self.engine = inference_engine
        self.encoder = ContextEncoder()
        self.comparer = VectorComparer()
        self.fuser = Fuser()
        self.feedback_loop = feedback_loop
        self.top_k = top_k

    def ask(self, question: str, query: ContextQuery, context: Optional[Dict] = None) -> Dict:
        """Return a suggested answer for ``question`` using optional ``context``."""
        all_ctx = self.provider.get_context(query)
        q_features = context or {}
        q_vec = self.encoder.encode(q_features)
        scored: List[Dict] = []
        for item in all_ctx:
            vec = item.get("vector")
            if vec is None:
                vec = self.encoder.encode(item.get("context", {}))
            score = self.comparer.cosine_similarity(q_vec, vec)
            scored.append({"item": item, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_items = [s["item"] for s in scored[: self.top_k]]
        fused = self.fuser.fuse({("qa", "", ""): top_items})
        answer = self.engine.predict({"question": question, "context": fused})
        if self.feedback_loop:
            suggestions = self.feedback_loop.suggest([], [answer])
            if suggestions:
                answer = suggestions[0]
        return {"answer": answer, "fused": fused}
