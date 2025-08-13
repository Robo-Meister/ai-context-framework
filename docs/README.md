# Documentation

This project ships developer guides and design notes as static HTML files.

- Open `dev/index.html` for developer-focused documentation.
- Open `theory/index.html` for theoretical background and architecture notes.

In the future these pages may move to a dedicated docs site (see
[docs/dev/TECHNICAL_ROADMAP.md](dev/TECHNICAL_ROADMAP.md)).


## Mass Testing

Before going live, stress test the goal feedback loop and learning pipeline with synthetic data:

```bash
pytest tests/test_goal_feedback_loop.py::test_goal_feedback_loop_randomized_batch \
       tests/test_feedback_pipeline.py::TestFeedbackPipeline::test_feedback_pipeline_randomized_batch
```

These tests generate many fake context maps to ensure the system behaves correctly under load. Extend them as needed for your own scenarios.
