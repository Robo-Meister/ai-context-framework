# Documentation

This project ships developer guides and design notes as static HTML and Markdown
files. You can browse them directly from the repository or render them through
MkDocs.

- Open `dev/index.html` for developer-focused documentation.
- Open `theory/index.html` for theoretical background and architecture notes.
- See `event-context-standard.md` for the event/context data model.
- Follow `getting_started/quickstart.md` for PyPI installation and pipeline
  examples.

To serve the documentation locally, install the docs extra and run MkDocs:

```bash
pip install caiengine[docs]
mkdocs serve
```

The site will be available at http://127.0.0.1:8000/ using the navigation from
`mkdocs.yml`.


## Mass Testing

Before going live, stress test the goal feedback loop and learning pipeline with synthetic data:

```bash
pytest tests/test_goal_feedback_loop.py::test_goal_feedback_loop_randomized_batch \
       tests/test_feedback_pipeline.py::TestFeedbackPipeline::test_feedback_pipeline_randomized_batch
```

These tests generate many fake context maps to ensure the system behaves correctly under load. Extend them as needed for your own scenarios.
