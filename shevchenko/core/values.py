from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field

import shevchenko.contracts.shapes as contract


# ─────────────────────────── Enums (closed vocabularies) ───────────────────────────

class Technology(str, Enum):
    PREFECT = "prefect"
    AIRFLOW = "airflow"
    INNGEST = "inngest"


class JobKind(str, Enum):
    DAG = "dag"
    SINGLE_AGENT = "single_agent"


class TriggerType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"
    EVENT = "event"
    MANUAL = "manual"


class DeploymentStatus(str, Enum):
    DEPLOYED = "deployed"
    FAILED = "failed"
    DRIFTED = "drifted"  # on-reach compare between the actual container checksum and stored checksum.
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"


# ─────────────────────────── Identity value objects ───────────────────────────
# Instead of bare str ids everywhere, give each id a type so they can't be mixed up.
class JobKey(BaseModel):
    model_config = {"frozen": True}
    value: str = Field(pattern=r"^[a-z0-9-]+$")  # "daily-stock-analysis"

    @classmethod
    def create(cls) -> "JobKey":
        return cls(value=uuid.uuid4().hex)


class JobId(BaseModel):
    key: JobKey
    version: int = Field(ge=1)

    @classmethod
    def create(cls) -> "JobId":
        return cls(key=JobKey.create(), version=1)


class DeploymentId(BaseModel):
    value: str = Field(pattern=r"^[0-9a-f]{32}$")  # uuid4().hex format

    @classmethod
    def create(cls) -> "DeploymentId":
        return cls(value=uuid.uuid4().hex)


class ScheduleId(BaseModel):
    value: str


class RunId(BaseModel):
    value: str


# ─────────────────────────── Schema description (was: dict) ───────────────────────────
# The I/O contract becomes real objects instead of {"ticker": "str"}.

class FieldType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"


class ParameterSpec(BaseModel):
    name: str
    type: FieldType
    required: bool = True
    description: str | None = None
    default: object | None = None


class ParameterSet(BaseModel):
    """Replaces a raw dict schema; a named collection with behavior."""
    parameters: list[ParameterSpec] = Field(default_factory=list)

    def names(self) -> list[str]:
        return [p.name for p in self.parameters]

    def required_names(self) -> list[str]:
        return [p.name for p in self.parameters if p.required]


class IOContract(BaseModel):
    inputs: ParameterSet
    outputs: ParameterSet


# ─────────────────────────── Descriptive metadata (was: str/tuple[str]) ───────────────────────────

class Tag(BaseModel):
    value: str = Field(pattern=r"^[a-z0-9-]+$")


class Category(BaseModel):
    value: str


class Intent(BaseModel):
    title: str
    summary: str
    description: str
    tags: list[Tag] = Field(default_factory=list)
    category: Category | None = None


# ─────────────────────────── Artifact & connection (was: str/dict) ───────────────────────────

class ImageReference(BaseModel):
    """Human-readable tag AND immutable digest, as we agreed."""
    tag: str  # "acme/stock:1.4.2"
    digest: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")


class SourceReference(BaseModel):
    commit: str
    build_id: str | None = None  # answers "which build run produced this?" —  (GitHub Actions run id e.g.)


class ContainerArtifact(BaseModel):
    image: ImageReference
    source: SourceReference

    def to_container_artifact_contract(self):
        return contract.ContainerArtifact(image_tag=self.image.tag,
                                          image_digest=self.image.digest,
                                          source_commit=self.source.commit.strip())


class SecretRef(BaseModel):
    """Pointer to a secret, never the secret itself."""
    store: str  # e.g. "vault" | "aws-sm"
    path: str


class ConnectionRef(BaseModel):
    endpoint: str
    auth: SecretRef


class StructureHash(BaseModel):
    value: str = Field(pattern=r"^[a-f0-9]+$")


# ─────────────────────────── Backend coordinates (was: opaque dict) ───────────────────────────
# Model per-technology coordinates as a typed union instead of a loose dict.

class PrefectCoordinates(BaseModel):
    technology: Technology = Technology.PREFECT
    deployment_id: str
    schedule_id: str | None = None  # only if you delegate scheduling


class AirflowCoordinates(BaseModel):
    technology: Technology = Technology.AIRFLOW
    dag_id: str


class InngestCoordinates(BaseModel):
    technology: Technology = Technology.INNGEST
    event_name: str
    event_key: SecretRef


BackendCoordinates = PrefectCoordinates | AirflowCoordinates | InngestCoordinates


# ─────────────────────────── Actors & provenance (was: str) ───────────────────────────

class Actor(BaseModel):
    id: str
    display_name: str | None = None


class TriggerSource(BaseModel):
    """Replaces 'schedule:<uid>' | 'manual:<user>' string encoding."""
    kind: TriggerType
    schedule_id: ScheduleId | None = None
    actor: Actor | None = None


class JobManifest(BaseModel):
    intent: Intent
    io: IOContract
    source_hint: str = "ai"  # "ai" | "author" — provisional vs confirmed
