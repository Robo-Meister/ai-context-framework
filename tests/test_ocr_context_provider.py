from datetime import datetime

from caiengine.objects.context_query import ContextQuery
from caiengine.objects.ocr_metadata import OCRSpan
from caiengine.providers.ocr_context_provider import OCRContextProvider


def test_ingest_ocr_document_emits_context():
    provider = OCRContextProvider()
    received = []
    provider.subscribe_context(received.append)

    span = OCRSpan(
        field_name="invoice_number",
        value="INV-001",
        bbox=(0.1, 0.2, 0.3, 0.4),
        page_number=1,
        confidence=0.92,
        offsets=(10, 17),
    )

    provider.ingest_ocr_document(
        raw_text="Invoice INV-001 total $123.45",
        document_type_hint="invoice",
        spans=[span],
        confidence_scores={"document": 0.87},
        language="en",
    )

    assert len(received) == 1
    event = received[0]
    context = event["context"]
    assert context["payload"]["text"].startswith("Invoice INV-001")
    assert context["payload"]["document_type_hint"] == "invoice"
    assert context["ocr_metadata"] is not None
    assert context["ocr_metadata"]["spans"][0]["field_name"] == "invoice_number"
    assert context["ocr_metadata"]["confidence_scores"]["document"] == 0.87


def test_fetch_structured_context_includes_spans():
    provider = OCRContextProvider()

    provider.ingest_ocr_document(
        raw_text="Resume: Jane Doe",
        document_type_hint="resume",
        spans=[
            {
                "field_name": "candidate_name",
                "value": "Jane Doe",
                "bbox": (0.0, 0.0, 0.5, 0.1),
                "confidence": 0.99,
            }
        ],
    )

    query = ContextQuery(
        roles=[],
        time_range=(datetime.min, datetime.max),
        scope="*",
        data_type="*",
    )

    contexts = provider.get_structured_context(query)
    assert len(contexts) == 1
    payload_spans = contexts[0].payload["spans"]
    assert payload_spans[0]["field_name"] == "candidate_name"
    assert contexts[0].ocr_metadata.spans[0].value == "Jane Doe"
