"""Learning interface contracts for training and inference components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LearningInterface(ABC):
    """Contract for components that can train, predict, and infer."""

    @abstractmethod
    def predict(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generate a prediction payload for structured input data.

        Args:
            input_data: Structured model input represented as a dictionary.

        Returns:
            A dictionary containing prediction output values.
        """

    @abstractmethod
    def train(self, input_data: dict[str, Any], target: float) -> float:
        """Train the learner on one input-target pair.

        Args:
            input_data: Structured model input represented as a dictionary.
            target: Expected numeric target value for the input.

        Returns:
            Numeric loss for the training step.
        """

    @abstractmethod
    def infer(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run inference from raw/fused input and include richer metadata.

        Args:
            input_data: Structured model input represented as a dictionary.

        Returns:
            A dictionary with inference output and related metadata.
        """
