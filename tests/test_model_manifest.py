from caiengine.objects.model_manifest import ModelManifest


def test_model_manifest_backward_compatible_defaults():
    manifest = ModelManifest(model_name="legacy", version="0.1")

    assert manifest.schema_version == "1.0"
    assert manifest.engine_version is None
    assert manifest.task is None
    assert manifest.tags == []
    assert manifest.input_schema == {}
    assert manifest.output_schema == {}
    assert manifest.created_at is None


def test_model_manifest_supports_extended_fields():
    manifest = ModelManifest(
        model_name="classifier",
        version="2.0",
        schema_version="2.1",
        engine_version="0.2.1",
        task="classification",
        tags=["nlp", "fast"],
        input_schema={"type": "text"},
        output_schema={"labels": ["a", "b"]},
        created_at="2026-01-01T12:00:00Z",
    )

    assert manifest.schema_version == "2.1"
    assert manifest.task == "classification"
    assert manifest.tags == ["nlp", "fast"]

def test_model_manifest_preserves_legacy_positional_training_context():
    manifest = ModelManifest("legacy", "0.1", "ctx")

    assert manifest.training_context == "ctx"
    assert manifest.schema_version == "1.0"
