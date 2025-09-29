from dataclasses import dataclass


@dataclass
class TokenUsage:
    """Simple data container tracking prompt and completion tokens."""
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def as_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class TokenCounter:
    """Aggregate token usage across multiple model invocations."""

    def __init__(self) -> None:
        self.usage = TokenUsage()

    def add(self, usage: "TokenUsage | dict") -> None:
        """Add a :class:`TokenUsage` or compatible dict to the aggregate."""
        if isinstance(usage, dict):
            usage = TokenUsage(**usage)
        self.usage.prompt_tokens += usage.prompt_tokens
        self.usage.completion_tokens += usage.completion_tokens

    def reset(self) -> None:
        """Reset the aggregate counts to zero."""
        self.usage = TokenUsage()

    def as_dict(self) -> dict:
        return self.usage.as_dict()
