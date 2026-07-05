import traceback
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import field_validator, ConfigDict, BaseModel, Field


class ReportStatus(str, Enum):
    DRAFT = "draft"  # created, not yet submitted  (only if 2-step)
    IN_PROGRESS = "in_progress"  # generation running
    COMPLETED = "completed"  # report is done & available
    FAILED = "failed"  # generation failed
    STALE = "stale"  # superseded (e.g. by a split)


class ValueObject(BaseModel):
    """Base for all value objects: frozen (immutable + hashable)."""
    model_config = ConfigDict(frozen=True)


class Ticker(ValueObject):
    symbol: str

    @field_validator("symbol")
    @classmethod
    def _normalize(cls, v: str) -> str:
        if not v or not v.replace(".", "").isalnum():
            raise ValueError(f"invalid ticker: {v!r}")
        return v.upper()


class ReportId(ValueObject):
    model_config = {"extra": "ignore"}
    value: str = Field(default_factory=lambda: str(uuid.uuid4()))


class FailureContext(ValueObject):
    # ponytail: automatically capture when the exception was caught
    caught_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: str
    error_type: Optional[str] = None

    @classmethod
    def from_exception(cls, exc: BaseException) -> "FailureContext":
        return cls(
            error_type=type(exc).__name__,
            details="".join(traceback.format_exception(exc)),
        )


class Provenance(ValueObject):
    # what inputs, from where, and when, produced this report?
    source: str  # "yfinance"
    source_version: str | None  # yfinance lib version, e.g. "0.2.40"
    query: str  # the raw query/symbol sent
    queried_at: datetime  # the adjustment/snapshot epoch


class SplitEvent(ValueObject):
    ex_date: date
    ratio: Decimal
    provenance: Provenance | None = None


class ReportPayload(ValueObject):
    model_config = ConfigDict(frozen=True)
    report_id: ReportId
    provenance: Provenance | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_prompt_context(self) -> str: ...

    def summary_focus(self) -> str: ...

    @classmethod
    def report_type(cls) -> str:
        return cls.__name__
