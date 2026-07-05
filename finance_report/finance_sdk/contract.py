from typing import Protocol, runtime_checkable

from .schemas import ReportTriggerRequest, ReportTriggerResponse


@runtime_checkable
class FinanceReportService(Protocol):
    """
    Structural contract for finance report operations.
    Any class implementing these methods is a valid FinanceReportService.
    """

    async def trigger_report_generation(
            self,
            report_trigger_request: ReportTriggerRequest
    ) -> ReportTriggerResponse:
        ...
