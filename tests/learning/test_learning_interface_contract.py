from caiengine.core.learning.learning_manager import LearningManager
from caiengine.interfaces.learning_interface import LearningInterface


def test_learning_manager_is_learning_interface() -> None:
    manager = LearningManager(input_size=4)
    assert isinstance(manager, LearningInterface)
