class PolicyEvaluator:
    """Simple rule-based policy evaluator.

    The evaluator maintains a collection of rule callables. Each rule is called
    with ``(context, prediction)`` and should return either ``True``/``False`` or
    a tuple ``(passed, prediction)``. In the latter case the returned prediction
    is passed to subsequent rules allowing them to modify it.
    """

    def __init__(self, rules=None):
        """Initialize the evaluator with an optional list of rules."""
        self.rules = list(rules) if rules else []

    def add_rule(self, rule_callable):
        """Register an additional rule."""
        self.rules.append(rule_callable)

    def evaluate(self, context: dict, prediction: dict | None = None) -> (bool, dict | None):
        """Evaluate all configured rules.

        Parameters
        ----------
        context:
            Context data being checked.
        prediction:
            Optional prediction that can be modified by the rules.

        Returns
        -------
        tuple[bool, dict | None]
            ``(passed, prediction)`` where ``prediction`` may be updated by the
            rules. ``passed`` is ``False`` if any rule fails.
        """

        current_pred = prediction
        for rule in self.rules:
            result = rule(context, current_pred)
            if isinstance(result, tuple):
                passed, new_pred = result
                if not passed:
                    return False, None
                current_pred = new_pred
            else:
                if not result:
                    return False, None
        return True, current_pred
