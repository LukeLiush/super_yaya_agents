# BackendPlugin Protocol (the verbs)

from typing import Protocol, runtime_checkable

from shevchenko.contracts.capabilities import Capabilities
from shevchenko.contracts.shapes import JobSpec, Coordinates, ParamValues, RunRef, RunResult, CronExpr


@runtime_checkable
class BackendPlugin(Protocol):
    # Identity + self-description
    technology: str  # e.g. "prefect" — open string

    def capabilities(self) -> Capabilities: ...

    # ── REQUIRED: the irreducible minimum every backend must do ──
    def deploy(self, job_spec: JobSpec) -> Coordinates: ...

    def invoke(self, coordinates: Coordinates, params: ParamValues) -> RunRef: ...

    def status(self, coordinates: Coordinates, run_ref: RunRef) -> RunResult: ...

    # ── OPTIONAL: guarded by capabilities(); core checks before calling ──
    def reschedule(self, coordinates: Coordinates, cron_expr: CronExpr) -> None: ...

    def pause(self, coordinates: Coordinates) -> None: ...

    def resume(self, coordinates: Coordinates) -> None: ...

    def cancel(self, coordinates: Coordinates, ref: RunRef) -> None: ...

    def teardown(self, coordinates: Coordinates) -> None: ...  # remove the deployment
