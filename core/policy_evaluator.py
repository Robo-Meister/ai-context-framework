class PolicyEvaluator:
    """
    Evaluates a set of policy rules against context and prediction data.
    Rejects or modifies inference output if rules are violated.
    """
    def __init__(self, rules=None):
        # rules is a list of callables: rule(context, prediction) -> bool
        self.rules = rules or []

    def add_rule(self, rule_callable):
        """
        Add a new rule callable.
        """
        self.rules.append(rule_callable)

    def evaluate(self, context: dict, prediction: dict) -> (bool, dict):
    # def evaluate(self, context_item: Dict[str, Any], prediction: dict) -> (bool, dict):
        """
        Evaluate all rules; return (passed, possibly modified prediction).
        If any rule returns False, fail the policy check.
        """
        for rule in self.rules:
            if not rule(context, prediction):
                # Could log or raise alerts here
                return False, None
        return True, prediction
