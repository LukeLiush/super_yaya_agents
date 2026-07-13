import logging
from typing import Any, cast

from finance_report.reporting_core.application.news.provider import NewsProvider
from finance_report.reporting_core.application.ports.report_repository import ReportPayloadRepository, \
    ReportRequestRepository
from finance_report.reporting_core.application.ports.unit_of_work import UnitOfWork
from finance_report.reporting_core.application.use_cases.create_report_request import UseCase
from finance_report.reporting_core.domain.events import ReportRequested
from finance_report.reporting_core.domain.news_report import NewsReport
from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.domain.shared_values import Ticker, FailureContext

logger = logging.getLogger(__name__)


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
            report_request_repository: ReportRequestRepository = uow.repository(cast(Any, ReportRequestRepository))
            report_request: ReportRequest | None = report_request_repository.get_by_id(report_requested.report_id)
            if report_request is None:
                logger.error("Report request not found: %s", report_requested.report_id)
                return None
            try:
                news_items, provenance = self._provider.fetch_latest_news(ticker)
                if news_items is None:
                    report_request.mark_as_failed(FailureContext.from_exception(
                        ValueError(f"No news items returned for ticker '{report_request.ticker}' "
                                   f"(report_id={report_request.id}, as_of={report_request.as_of}, ")))
                    report_request_repository.add(report_request)
                    return None
                news_report = NewsReport.create(
                    report_id=report_requested.report_id,
                    items=news_items,
                    provenance=provenance,
                )
                uow.repository(cast(Any, ReportPayloadRepository)).add(news_report)

            except Exception as e:
                logger.error("Error fetching news: %s", e)
                report_request.mark_as_failed(
                    FailureContext.from_exception(e)
                )
                report_request_repository.add(report_request)
                return None

        return news_report
