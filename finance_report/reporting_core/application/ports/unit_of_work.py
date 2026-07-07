from typing import Any, Protocol, TypeVar

T = TypeVar(
    "T",
)


class UnitOfWork(Protocol):
    def repository(self, repository_type: type[T]) -> T: ...

    def __enter__(self) -> Any: ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> Any: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
