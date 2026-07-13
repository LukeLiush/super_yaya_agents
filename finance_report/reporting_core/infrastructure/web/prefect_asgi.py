import logging
from typing import TYPE_CHECKING

from fastapi import FastAPI
from prefect.deployments import run_deployment

from finance_report.finance_sdk.schemas import ReportTriggerRequest, ReportTriggerResponse
from finance_report.reporting_core.infrastructure.config.settings import get_settings
from finance_report.reporting_core.infrastructure.web.asgi_adapter import ASGIAdapter
from finance_report.reporting_core.infrastructure.config.settings import Settings

if TYPE_CHECKING:
    from prefect.client.schemas.objects import FlowRun

logger = logging.getLogger(__name__)


class PrefectASGI(ASGIAdapter):
    async def trigger(self, request: ReportTriggerRequest) -> ReportTriggerResponse:
        # result: ReportRunResult = await finance_report_flow(request, requested_by="shua@")
        _settings: Settings = await get_settings()
        flow_run: FlowRun = await run_deployment(  # type: ignore[misc, assignment]
            name=_settings.prefect_deployment_name,
            parameters={"report_trigger_request": request.model_dump(), "requested_by": "api"},
            timeout=0,  # don't wait for completion — return as soon as it's scheduled
        )
        return ReportTriggerResponse(
            ticker=request.ticker,
            id=str(flow_run.id),
            message=f"Queued: {_settings.prefect_server_url}/runs/flow-run/{flow_run.id}",
        )

    def attach_to_app(self, app: FastAPI) -> None:
        # noop
        pass
