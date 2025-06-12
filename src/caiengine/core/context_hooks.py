"""Hook system for reacting to context updates."""

from dataclasses import dataclass
from typing import Callable, List

from caiengine.interfaces.network_interface import NetworkInterface


@dataclass
class ContextHook:
    """Represents a hook triggered by context changes."""

    condition: Callable[[str, dict], bool]
    action: Callable[[str, dict, NetworkInterface], None]


class ContextHookManager:
    """Manage context hooks and trigger them on updates."""

    def __init__(self):
        self._hooks: List[ContextHook] = []

    def register_hook(self, condition: Callable[[str, dict], bool], action: Callable[[str, dict, NetworkInterface], None]):
        self._hooks.append(ContextHook(condition, action))

    def trigger(self, key: str, value: dict, network: NetworkInterface):
        for hook in self._hooks:
            if hook.condition(key, value):
                hook.action(key, value, network)
