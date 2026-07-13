# shevchenko/persistence/repositories.py  — where the record goes
from typing import Protocol

from shevchenko.core.values import JobId, JobKey
from shevchenko.core.job import Job


class JobRepository(Protocol):
    def get(self, job_id: JobId) -> Job: ...

    def list_versions(self, job_key: JobKey) -> list[int]: ...

    def save(self, job: Job) -> None: ...
