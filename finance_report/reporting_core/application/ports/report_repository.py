from typing import Protocol, TypeVar, runtime_checkable

from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.domain.shared_values import ReportId, ReportPayload

T = TypeVar("T", bound=ReportPayload)


@runtime_checkable
class ReportPayloadRepository(Protocol):
    def add(self, report_payload: ReportPayload) -> None: ...

    def get_by_id(self, report_id: str, report_type: type[T]) -> T: ...


class ReportRequestRepository(Protocol):
    def add(self, report_request: ReportRequest) -> None: ...

    def get_by_id(self, report_id: ReportId) -> ReportRequest | None: ...
