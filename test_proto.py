from typing import Protocol, TypeVar, Generic
T = TypeVar("T", contravariant=True)
class EventBus(Protocol, Generic[T]):
    def emit(self, event: T) -> None:
        ...
