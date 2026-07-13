from typing import Protocol, TypeVar

from pydantic import BaseModel

from finance_report.reporting_core.application.market_data.provider import SplitProvider
from finance_report.reporting_core.application.ports.report_repository import ReportRequestRepository
from finance_report.reporting_core.application.ports.unit_of_work import UnitOfWork
from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.domain.shared_values import Ticker

TInput = TypeVar("TInput", contravariant=True)
TOutput = TypeVar("TOutput", covariant=True)


class UseCase(Protocol[TInput, TOutput]):
    async def run(self, request: TInput) -> TOutput: ...


class CreateRequestInput(BaseModel):
    ticker: Ticker
    requested_by: str


class CreateReportRequestUseCase(UseCase[CreateRequestInput, ReportRequest]):
    def __init__(
        self,
        split_provider: SplitProvider,
        uow: UnitOfWork,
    ) -> None:
        self._split_provider = split_provider
        self._uow: UnitOfWork = uow

    async def run(self, request: CreateRequestInput) -> ReportRequest:
        ticker = request.ticker
        requested_by = request.requested_by
        split_event = self._split_provider.fetch_latest_splits(ticker)

        with self._uow as uow:
            report_request: ReportRequest = ReportRequest.create(ticker, requested_by, split_event)
            report_request_repository: ReportRequestRepository = uow.repository(ReportRequestRepository)
            report_request_repository.add(report_request)
        return report_request
