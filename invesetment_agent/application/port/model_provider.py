from typing import Any, Protocol


class ModelProvider(Protocol):
    def get_model(self, model_name: str) -> Any:  # returns a pydantic-ai model
        ...
