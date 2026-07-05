from typing import Optional

from .provider import NewsProvider
from ..ports.report_repository import ReportPayloadRepository
from ..ports.unit_of_work import UnitOfWork
from ..use_cases.create_report_request import UseCase
from ...domain.events import ReportRequested
from ...domain.news_report import NewsReport
from ...domain.shared_values import Ticker


class GenerateNewsReportUseCase(UseCase[ReportRequested, Optional[NewsReport]]):
    def __init__(self,
                 provider: NewsProvider,
                 uow: UnitOfWork) -> None:
        self._provider: NewsProvider = provider
        self._uow = uow

    async def run(self, report_requested: ReportRequested) -> Optional[NewsReport]:
        ticker: Ticker = report_requested.ticker
        news_items, provenance = self._provider.fetch_latest_news(ticker)
        news_report = NewsReport.create(report_id=report_requested.report_id,
                                        items=news_items,
                                        provenance=provenance, )
        with self._uow as uow:
            uow.repository(ReportPayloadRepository).save(news_report)

        return news_report
