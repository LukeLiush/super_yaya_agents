from datetime import UTC, datetime, timezone
from datetime import date as Date

from pydantic import BaseModel, ConfigDict, Field

from finance_report.reporting_core.domain.events import ReportRequested
from finance_report.reporting_core.domain.exceptions import InvalidStateTransition
from finance_report.reporting_core.domain.shared_values import (
    FailureContext,
    ReportId,
    ReportStatus,
    SplitEvent,
    Ticker,
)


class ReportRequest(BaseModel):
    model_config = ConfigDict(validate_assignment=True)
    ticker: Ticker
    split_event: SplitEvent | None = None
    requested_by: str

    id: ReportId = Field(default_factory=ReportId)
    as_of: Date = Field(default_factory=lambda: datetime.now(UTC).date())
    status: ReportStatus = ReportStatus.DRAFT

    failure_context: FailureContext | None = None

    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @classmethod
    def create(cls, ticker: Ticker, requested_by: str, split_event: SplitEvent | None) -> "ReportRequest":
        report_request = cls(ticker=ticker, requested_by=requested_by, split_event=split_event)
        return report_request

    def report_requested(self) -> ReportRequested:
        return ReportRequested(report_id=self.id, ticker=self.ticker, requested_by=self.requested_by)

    def _touch(self, *, complete: bool = False) -> None:
        now = datetime.now(UTC)
        self.updated_at = now
        if complete:
            self.completed_at = now

    def mark_as_in_progress(self) -> None:
        if self.status != ReportStatus.DRAFT:
            raise InvalidStateTransition(f"Cannot start a report in status {self.status}")
        self.status = ReportStatus.IN_PROGRESS
        self._touch(complete=False)

    def mark_as_failed(self, failure_context: FailureContext) -> None:
        self.status = ReportStatus.FAILED
        self.failure_context = failure_context
        self._touch(complete=True)

    def mark_as_complete(self) -> None:
        self.status = ReportStatus.COMPLETED
        self._touch(complete=True)
