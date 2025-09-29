from caiengine.common import AuditLogger
from caiengine.pipelines.context_pipeline import ContextPipeline
from caiengine.providers.mock_context_provider import MockContextProvider


def test_audit_logger_tracks_steps():
    audit = AuditLogger()
    pipeline = ContextPipeline(MockContextProvider(), audit_logger=audit)
    pipeline.run([], [])
    steps = [r["step"] for r in audit.get_records() if r["pipeline"] == "ContextPipeline"]
    assert "run_start" in steps
    assert "fused" in steps
