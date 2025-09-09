from caiengine.pipelines.intent_pipeline import IntentPipeline


def test_intent_pipeline_processes_message():
    pipeline = IntentPipeline()
    result = pipeline.process("Can I return this? I want to buy another.")
    assert result[0]["funnel_stage"] == "retention"
    assert result[1]["funnel_stage"] == "conversion"
