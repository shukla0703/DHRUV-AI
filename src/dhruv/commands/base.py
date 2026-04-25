from __future__ import annotations

from abc import ABC, abstractmethod


class Command(ABC):
    @abstractmethod
    def matches(self, user_input: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def execute(self, user_input: str) -> str:
        raise NotImplementedError
