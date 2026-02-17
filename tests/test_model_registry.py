import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Dynamically load modules to avoid importing heavy package dependencies
model_registry_spec = importlib.util.spec_from_file_location(
    "model_registry", ROOT / "src" / "caiengine" / "network" / "model_registry.py"
)
model_registry_module = importlib.util.module_from_spec(model_registry_spec)
model_registry_spec.loader.exec_module(model_registry_module)
ModelRegistry = model_registry_module.ModelRegistry

file_registry_spec = importlib.util.spec_from_file_location(
    "file_model_registry", ROOT / "src" / "caiengine" / "providers" / "file_model_registry.py"
)
file_registry_module = importlib.util.module_from_spec(file_registry_spec)
file_registry_spec.loader.exec_module(file_registry_module)
FileModelRegistry = file_registry_module.FileModelRegistry


class TestModelRegistry(unittest.TestCase):
    def test_register_and_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = FileModelRegistry(tmp)
            registry = ModelRegistry(backend)
            registry.register("test-model", "1", {"value": 1})
            registry.register("test-model", "2", {"value": 2})

            models = registry.list()
            self.assertEqual(len(models), 2)

            fetched = registry.fetch("test-model", "2")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["manifest"], {"value": 2})

            fetched_old = registry.fetch("test-model", "1")
            self.assertEqual(fetched_old["manifest"], {"value": 1})

    def test_find_with_metadata_criteria(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = FileModelRegistry(tmp)
            registry = ModelRegistry(backend)

            registry.register(
                "menu-classifier",
                "1.0",
                {
                    "artifact_path": "artifacts/menu-classifier-v1.bin",
                    "manifest": {
                        "task": "categorization",
                        "engine_version": "0.2.1",
                        "tags": ["pl", "meals"],
                    },
                },
            )
            registry.register(
                "sentiment-analyzer",
                "1.0",
                {
                    "artifact_path": "artifacts/sentiment-v1.bin",
                    "manifest": {
                        "task": "classification",
                        "engine_version": "0.3.0",
                        "tags": ["en", "reviews"],
                    },
                },
            )

            category_models = registry.find({"task": "categorization"})
            self.assertEqual([m["id"] for m in category_models], ["menu-classifier"])

            wildcard_engine = registry.find({"engine_version": "0.2.*"})
            self.assertEqual([m["id"] for m in wildcard_engine], ["menu-classifier"])

            tagged_models = registry.find({"tags": ["pl", "meals"]})
            self.assertEqual([m["id"] for m in tagged_models], ["menu-classifier"])

            no_match = registry.find({"tags": ["pl", "reviews"]})
            self.assertEqual(no_match, [])


if __name__ == "__main__":
    unittest.main()
