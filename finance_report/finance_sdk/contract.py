from typing import Protocol, runtime_checkable

from finance_report.finance_sdk.schemas import ReportTriggerRequest, ReportTriggerResponse


@runtime_checkable
class FinanceReportService(Protocol):
    """
    Structural contract for finance report operations.
    Any class implementing these methods is a valid FinanceReportService.
    """

    async def trigger_report_generation(
        self, report_trigger_request: ReportTriggerRequest
    ) -> ReportTriggerResponse: ...
