import logging

from fastapi import FastAPI
from prefect.deployments import run_deployment

from ..config.settings import settings
from ...infrastructure.web.asgi_adapter import ASGIAdapter
from ....finance_sdk.schemas import ReportTriggerResponse, ReportTriggerRequest

logger = logging.getLogger(__name__)


class PrefectASGI(ASGIAdapter):

    async def trigger(self, request: ReportTriggerRequest) -> ReportTriggerResponse:
        # result: ReportRunResult = await finance_report_flow(request, requested_by="shua@")

        flow_run = await run_deployment(
            name=settings.prefect_flow_name,
            parameters={"report_trigger_request": request.model_dump(), "requested_by": "api"},
            timeout=0,  # don't wait for completion — return as soon as it's scheduled
        )
        return ReportTriggerResponse(
            ticker=request.ticker,
            id=str(flow_run.id),
            message=f"Queued: {settings.prefect_server_url}/runs/flow-run/{flow_run.id}",
        )

    def attach_to_app(self, app: FastAPI) -> None:
        # noop
        pass
