import logging

from fastapi import FastAPI

from finance_report.finance_sdk.schemas import ReportTriggerRequest, ReportTriggerResponse
from finance_report.reporting_core.infrastructure.config.container import container
from finance_report.reporting_core.infrastructure.web.asgi_adapter import ASGIAdapter

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

_app = FastAPI()


@_app.get("/health")
async def health():
    return {"status": "ok"}


@_app.post("/report/trigger", response_model=ReportTriggerResponse, status_code=202)
async def trigger_report(request: ReportTriggerRequest):
    asgi: ASGIAdapter = container[ASGIAdapter]
    asgi.attach_to_app(_app)
    return await asgi.trigger(request)
