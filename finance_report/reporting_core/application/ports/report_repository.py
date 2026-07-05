from typing import Protocol, TypeVar, runtime_checkable, Optional, Type

from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.domain.shared_values import ReportPayload, ReportId

T = TypeVar("T", bound=ReportPayload)


@runtime_checkable
class ReportPayloadRepository(Protocol):
    def save(self, report_payload: ReportPayload) -> None:
        ...

    def get_by_id(self, report_id: str, report_type: Type[T]) -> T:
        ...


class ReportRequestRepository(Protocol):
    def save(self, report_request: ReportRequest) -> None:
        ...

    def get_by_id(self, report_id: ReportId) -> Optional[ReportRequest]:
        ...
