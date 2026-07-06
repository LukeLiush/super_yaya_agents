import httpx

from finance_report.finance_sdk.contract import FinanceReportService
from finance_report.finance_sdk.schemas import ReportTriggerRequest, ReportTriggerResponse


class HttpFinanceReportClient(FinanceReportService):
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",  # your FastAPI app, not Inngest's 8288
        timeout_in_seconds: int = 10,
    ) -> None:
        self.trigger_url = f"{base_url.rstrip('/')}/report/trigger"
        self.timeout_in_seconds = timeout_in_seconds

    async def trigger_report_generation(
        self,
        report_trigger_request: ReportTriggerRequest,
    ) -> ReportTriggerResponse:
        """Trigger report generation by calling the FastAPI /report/trigger endpoint.

        Fire-and-forget: the endpoint returns 202 Accepted and the workflow runs
        asynchronously via Inngest.
        """
        payload = report_trigger_request.model_dump()

        async with httpx.AsyncClient(timeout=self.timeout_in_seconds) as http:
            resp = await http.post(self.trigger_url, json=payload)
            resp.raise_for_status()
            body = resp.json()

        # The endpoint returns a serialized ReportTriggerResponse.
        return ReportTriggerResponse.model_validate(body)
