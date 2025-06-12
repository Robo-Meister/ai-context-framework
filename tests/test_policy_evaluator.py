import unittest
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "policy_evaluator",
    Path(__file__).resolve().parents[1] / "src" / "caiengine" / "core" / "policy_evaluator.py",
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
PolicyEvaluator = module.PolicyEvaluator

class TestPolicyEvaluator(unittest.TestCase):
    def test_policy_pass_and_modify(self):
        def rule_role(ctx, pred):
            return ctx.get('role') == 'admin'

        def rule_modify(ctx, pred):
            new_pred = dict(pred or {})
            new_pred['checked'] = True
            return True, new_pred

        evaluator = PolicyEvaluator([rule_role, rule_modify])
        ok, result = evaluator.evaluate({'role': 'admin'}, {'value': 1})
        self.assertTrue(ok)
        self.assertEqual(result, {'value': 1, 'checked': True})

    def test_policy_reject(self):
        def rule_fail(ctx, pred):
            return ctx.get('allowed', False)

        evaluator = PolicyEvaluator([rule_fail])
        ok, result = evaluator.evaluate({'allowed': False}, {})
        self.assertFalse(ok)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
