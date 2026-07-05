from typing import Protocol

from fastapi import FastAPI

from ....finance_sdk.schemas import ReportTriggerRequest, ReportTriggerResponse


class ASGIAdapter(Protocol):
    async def trigger(self, request: ReportTriggerRequest) -> ReportTriggerResponse:
        ...

    def attach_to_app(self, app: FastAPI) -> None: ...
