# agnostic wire shapes: JobSpec, Coordinates, RunRef, RunResult,

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TypeVar, Generic

from pydantic import BaseModel, Field, model_validator


# ── What the core hands DOWN to a plugin ─────────────────────────────

class ParameterSpec(BaseModel):
    name: str
    type: str  # "string" | "integer" | ... (open, not enum)
    required: bool = True
    default: object | None = None


class IOContract(BaseModel):
    inputs: list[ParameterSpec] = Field(default_factory=list)
    outputs: list[ParameterSpec] = Field(default_factory=list)


class ContainerArtifact(BaseModel):
    """What actually runs. Agnostic: every backend runs *something* addressable."""
    image_tag: str
    image_digest: str  # sha256, immutable — the truth
    source_commit: str | None = None


class JobSpec(BaseModel):
    """The agnostic description of a deployable job.
       No nodes/edges — the DAG internals live in the container, opaque to core."""
    id: str
    version: int
    io: IOContract
    container_artifact: ContainerArtifact


class ParamValues(BaseModel):
    """Runtime inputs crossing down to invoke()."""
    values: dict[str, object] = Field(default_factory=dict)


class CronExpr(BaseModel):
    expression: str
    timezone: str = "UTC"


# ── What a plugin hands BACK to the core ─────────────────────────────
class Handle(BaseModel):
    """Base for all plugin handles. Enforced flat: str keys -> scalar values only."""

    model_config = {"extra": "forbid"}  # no surprise fields

    @model_validator(mode="after")
    def _enforce_flat(self):
        for name, value in self.__dict__.items():
            permitted_primitives = (str, int, float, bool)
            if not isinstance(value, permitted_primitives) or isinstance(value, BaseModel):
                raise ValueError(
                    f"Handle field '{name}' must be a scalar ({permitted_primitives}); "
                    f"nesting is not allowed, got {type(value).__name__}"
                )
        return self


H = TypeVar("H", bound=Handle)


class Coordinates(BaseModel, Generic[H]):
    """The plugin's OWN handle to what it deployed — OPAQUE to the core.
       Core stores and returns it verbatim; only the plugin interprets it."""
    technology: str
    handle: H  # prefect puts deployment_id for prefect, or dag id for airflow, etc.


class RunRef(BaseModel):
    """A plugin's reference to one execution. Opaque to core, stored verbatim."""
    value: dict[str, object]  # airflow needs dag_id+run_id; core doesn't care


class RunStatus(str, Enum):
    """The ONE normalized vocabulary. Plugins map their words into this."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"  # honest state — not every backend can tell


class RunResult(BaseModel):
    status: RunStatus
    ref: RunRef
    output: dict[str, object] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
