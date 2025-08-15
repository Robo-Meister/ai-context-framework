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
            self.assertEqual(fetched["data"], {"value": 2})

            fetched_old = registry.fetch("test-model", "1")
            self.assertEqual(fetched_old["data"], {"value": 1})


if __name__ == "__main__":
    unittest.main()
