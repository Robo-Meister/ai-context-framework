# Documentation

This project ships developer guides, design notes, and getting-started material
as static HTML and Markdown. You can browse them directly from the repository
or render them through MkDocs.

## What's inside

- `dev/index.html`: developer-focused documentation.
- `theory/index.html`: theoretical background and architecture notes.
- `event-context-standard.md`: event/context data model reference.
- `getting_started/quickstart.md`: PyPI installation and pipeline examples.
- `examples/`: additional usage walkthroughs and experiments.
- `status/`: current project status notes.

## Serve the docs locally

Install the docs extra and run MkDocs:

```bash
pip install caiengine[docs]
mkdocs serve
```

The site will be available at http://127.0.0.1:8000/ using the navigation from
`mkdocs.yml`.

## Build the static site

```bash
pip install caiengine[docs]
mkdocs build --clean
```

The generated site will be written to the `site/` directory by default.

## Mass testing

Before going live, stress test the goal feedback loop and learning pipeline
with synthetic data:

```bash
pytest tests/test_goal_feedback_loop.py::test_goal_feedback_loop_randomized_batch \
       tests/test_feedback_pipeline.py::TestFeedbackPipeline::test_feedback_pipeline_randomized_batch
```

These tests generate many fake context maps to ensure the system behaves
correctly under load. Extend them as needed for your own scenarios.
