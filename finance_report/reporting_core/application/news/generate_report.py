from typing import Any, cast

from finance_report.reporting_core.application.news.provider import NewsProvider
from finance_report.reporting_core.application.ports.report_repository import ReportPayloadRepository
from finance_report.reporting_core.application.ports.unit_of_work import UnitOfWork
from finance_report.reporting_core.application.use_cases.create_report_request import UseCase
from finance_report.reporting_core.domain.events import ReportRequested
from finance_report.reporting_core.domain.news_report import NewsReport
from finance_report.reporting_core.domain.shared_values import Ticker


class GenerateNewsReportUseCase(UseCase[ReportRequested, NewsReport | None]):
    def __init__(self, provider: NewsProvider, uow: UnitOfWork) -> None:
        self._provider: NewsProvider = provider
        self._uow = uow

    async def run(self, report_requested: ReportRequested) -> NewsReport | None:
        ticker: Ticker = report_requested.ticker
        news_items, provenance = self._provider.fetch_latest_news(ticker)
        news_report = NewsReport.create(
            report_id=report_requested.report_id,
            items=news_items,
            provenance=provenance,
        )
        with cast(Any, self._uow) as uow:
            uow.repository(cast(Any, ReportPayloadRepository)).save(news_report)

        return news_report
