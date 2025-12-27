from abc import ABC, abstractmethod
from typing import List


class SingleAgentService(ABC):

    @abstractmethod
    def get_answer(self, query: str, instructions: List[str]) -> str:
        raise NotImplementedError("Subclasses must implement get_answer method")
