import sqlite3
from collections.abc import Callable
from typing import TypeVar

from finance_report.reporting_core.application.ports.unit_of_work import UnitOfWork

T = TypeVar("T")


class SqliteUnitOfWork(UnitOfWork):
    def __init__(self, repository_factories: dict[type, Callable[[sqlite3.Connection], T]], db_path=":memory:"):
        self._repository_factories: dict[type, Callable[[sqlite3.Connection], T]] = repository_factories
        self._repositories: dict[type, T] = {}
        self._connection = None
        self._db_path = db_path

    def repository(self, repository_type: type[T]) -> T:
        if self._connection is None:
            raise RuntimeError("UnitOfWork not initialized. Use 'with uow:' block.")

        if repository_type not in self._repositories:
            if repository_type not in self._repository_factories:
                raise ValueError(f"No factory registered for repository type: {repository_type}")

            self._repositories[repository_type] = self._repository_factories[repository_type](self._connection)

        return self._repositories[repository_type]

    def __enter__(self):
        self._connection = sqlite3.connect(self._db_path)
        self._connection.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                self.rollback()
            else:
                self.commit()
        finally:
            if self._connection:
                self._connection.close()
                self._connection = None
            self._repositories.clear()

    def commit(self):
        if self._connection:
            self._connection.commit()

    def rollback(self):
        if self._connection:
            self._connection.rollback()
