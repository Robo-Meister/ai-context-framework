# Integrating OCR Pipelines with CAIEngine

This guide describes how to connect an existing OCR service that already produces
plain text, document type predictions, and preliminary key/value candidates with
CAIEngine so you can replace brittle regular-expression post-processing with the
framework's context routing and inference hooks.

## 1. High-Level Flow

1. **Run OCR outside of CAIEngine.** Use your OCR system to obtain (a) the raw
   text of each document and (b) any metadata it provides such as page
   segmentation, document type guesses, or candidate key/value pairs.
2. **Wrap OCR output in a `ContextProvider`.** Create a provider class that
   yields `ContextItem` objects representing each document or logical section.
   Attach the OCR metadata to the context payload so downstream modules can use
   it for scoring and extraction.
3. **Apply CAIEngine's deduplication and categorization stages.** Use the
   built-in `Deduplicator` and `Categorizer` modules to cluster content snippets
   and filter noise. You can feed your OCR type guess into the categorizer as an
   initial signal, while allowing the engine's embedding similarity and rules to
   refine the classification.
4. **Fuse signals into a clean record.** Configure the `Fuser` to consolidate
   overlapping snippets (e.g., repeated headers) and to merge OCR metadata with
   context-based insights.
5. **Invoke an `AIInferenceEngine`.** Implement an inference hook that maps the
   fused context into your structured schema (résumé, invoice, contract, etc.).
   This component can use LLM prompts, ML classifiers, or deterministic logic
   tailored to your domain.
6. **Export to your target format.** After inference, serialize the structured
   data into the format your downstream systems expect (JSON, CSV, database
   rows, etc.).

## 2. Implementing the OCR Context Provider

Create a provider class under `src/caiengine/providers` (or your preferred
module) that reads OCR output (files, API responses, or database rows) and yields
`ContextItem` instances. Include fields such as:

- `raw_text`: the OCR-extracted text.
- `document_type_hint`: the OCR service's predicted type (e.g., invoice, CV).
- `spans`: offsets or bounding boxes for each candidate field the OCR detected.
- `confidence_scores`: numeric confidence metrics from the OCR service.

By keeping these signals inside the context, CAIEngine modules can incorporate
confidence and structural hints rather than relying on regexes.

## 3. Smarter Categorization than Regex

Instead of regular expressions, leverage the `TextEmbeddingComparer` plus your
OCR metadata:

- Seed the categorizer with representative exemplars for each document type.
- Combine embedding similarity with the OCR-provided `document_type_hint` to
  boost accuracy (e.g., accept the OCR label only if similarity exceeds a
  threshold; otherwise fall back to the most similar exemplar).
- Store hard rules only for high-precision cues (e.g., specific tax identifiers)
  rather than broad regex heuristics.

This hybrid approach reduces false positives and allows the categorizer to adapt
as you feed more training data.

### 3.1 Extending the Categorizer for OCR Signals

For tricky OCR documents—such as those with mixed languages, tables embedded as
images, or heavily rotated scans—augment the categorizer with richer signals so
it can disambiguate near-duplicate content:

1. **Create OCR-aware features.** In your `ContextItem` payload, add fields that
   capture layout hints (page numbers, column indexes), language detection
   results, and OCR confidence scores. These features give the categorizer more
   than just text similarity when deciding among competing categories.
2. **Add metadata-based scorers.** Implement a custom `SimilarityScorer` that
   rewards matches where the OCR metadata aligns with category expectations
   (e.g., invoices usually contain currency symbols; resumes reference job
   titles). Register this scorer alongside the default embedding comparer.
3. **Handle weak OCR predictions.** When the OCR engine emits low-confidence
   labels, fall back to embedding similarity plus rule-based overrides. This
   prevents a noisy OCR guess from locking the item into the wrong category.
4. **Log ambiguous assignments.** Track cases where the categorizer returns
   multiple candidates with close scores. Review these examples, tune your OCR
   pipeline (deskewing, contrast boosting), and add new exemplars to narrow the
   margin over time.

By enriching the categorizer with OCR-specific metadata and feedback, you can
support documents that would otherwise be misrouted by pure text similarity or
regex heuristics.

### 3.2 Returning Structured OCR Fields with Spatial Context

Meeting downstream OCR consumers—such as invoice ingestion systems that expect
values plus their on-page position—typically requires augmenting the categorizer
with a richer payload than just raw text. A practical recipe is:

1. **Preserve whitespace-aligned text.** Instead of normalising all whitespace,
   keep the OCR provider's spacing so you can reconstruct columnar layouts
   (tables, totals blocks). Store both the raw text and a "display" version that
   pads each line with spaces to mirror the original grid. Your
   `ContextItem.payload` might expose `{"text": raw_text, "display_text": formatted_text}`.
2. **Attach geometric spans per candidate field.** Include bounding boxes or
   character-offset ranges for key OCR detections (invoice number, line items,
   totals). For example, add `{"field": "invoice_number", "bbox": [x1, y1, x2, y2]}`
   entries. When the categorizer selects a document type, downstream inference
   can recover both the value and its location.
3. **Score against layout-aware prototypes.** Seed each category with exemplar
   snippets that include structured hints (e.g., a JSON blob of expected fields
   and their spatial relationships). Implement a custom `SimilarityScorer` that
   rewards OCR items whose detected fields align with the exemplar schema—helping
   distinguish invoices with line-item tables from quotes or purchase orders.
4. **Emit structured context for inference.** After categorization, package the
   enriched OCR payload into the fused context so your `AIInferenceEngine` can
   format the final record. For invoices, the inference step can iterate over the
   `line_items` span list, reconstruct each row's text via the preserved spacing,
   and output an ordered table alongside header fields such as invoice number and
   totals.

These additions let the categorizer maintain spatial fidelity while still
benefiting from embedding similarity and metadata signals.

## 4. Structured Extraction via Inference Engines

Inside your `AIInferenceEngine` implementation:

1. Receive the fused context items plus OCR metadata.
2. Prompt an LLM or run a classifier to extract fields such as totals, vendor
   names, employment dates, or contract clauses.
3. Use the OCR `spans`/coordinates to map extracted values back to the original
   document for auditing or highlighting.
4. Validate required fields (e.g., totals > 0, presence of currency) before
   finalizing the record.

Because the inference layer works on cleaned, categorized context, it can focus
on semantic extraction rather than compensating for noisy regex groupings.

## 5. Output Formatting and Feedback Loops

After extraction, push the structured record to your downstream format. Capture
feedback from users (corrections, approvals) and feed it into CAIEngine's goal
feedback loop so the categorizer and inference prompts improve over time.

By isolating OCR as a pre-processing step and letting CAIEngine handle context
management, categorization, and inference, you can replace fragile regex logic
with a modular pipeline that is easier to extend and maintain.
