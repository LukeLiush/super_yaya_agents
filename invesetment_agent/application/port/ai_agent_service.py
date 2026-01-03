from abc import ABC, abstractmethod


class AgentService(ABC):
    @abstractmethod
    def get_answer(self, query: str) -> str:
        raise NotImplementedError("Subclasses must implement get_answer method")
