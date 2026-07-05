import datetime

import inngest
import inngest.fast_api
from fastapi import FastAPI

from finance_report.finance_sdk.schemas import ReportTriggerRequest, ReportTriggerResponse
from finance_report.reporting_core.infrastructure.flows.inngest_finance_report_service import \
    InngestFinanceReportService, ReportRunResult
from finance_report.reporting_core.infrastructure.web.asgi_adapter import ASGIAdapter


class InngestASGI(ASGIAdapter):
    def __init__(
            self,
            inngest_finance_report_service: InngestFinanceReportService,
            inngest_client: inngest.Inngest,
    ) -> None:
        self._report_service = inngest_finance_report_service
        self._inngest_client = inngest_client

    async def trigger(self, request: ReportTriggerRequest) -> ReportTriggerResponse:
        ids = await self._inngest_client.send(
            inngest.Event(name="app/report.requested", data=request.model_dump())
        )
        return ReportTriggerResponse(ticker=request.ticker, id=", ".join(ids), message="Report generation task queued")

    def _build_report_function(self):
        async def _handle_report_request(ctx: inngest.Context) -> ReportRunResult:
            request = ReportTriggerRequest.model_validate(ctx.event.data)
            return await self._report_service.run_report_generation(request, ctx)

        # Apply the decorator as a normal function call at instance-creation time.
        return self._inngest_client.create_function(
            fn_id="request-report",
            trigger=inngest.TriggerEvent(event="app/report.requested"),
            throttle=inngest.Throttle(
                limit=2, period=datetime.timedelta(minutes=1)
            ),
            output_type=ReportRunResult,
        )(_handle_report_request)

    def attach_to_app(self, app: FastAPI) -> None:
        _function = self._build_report_function()
        inngest.fast_api.serve(
            app,
            self._inngest_client,
            [_function], )
