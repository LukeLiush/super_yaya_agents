import datetime as dt
import logging
from datetime import datetime
from typing import Any, cast

from finance_report.reporting_core.application.insider_filling.provider import InsiderProvider
from finance_report.reporting_core.application.ports.report_repository import ReportPayloadRepository, \
    ReportRequestRepository
from finance_report.reporting_core.application.ports.unit_of_work import UnitOfWork
from finance_report.reporting_core.application.use_cases.create_report_request import UseCase
from finance_report.reporting_core.domain.events import ReportRequested
from finance_report.reporting_core.domain.insider_report import InsiderReport
from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.domain.shared_values import FailureContext

logger = logging.getLogger(__name__)


class GenerateInsiderReportUseCase(UseCase[ReportRequested, InsiderReport | None]):
    def __init__(self, provider: InsiderProvider, uow: UnitOfWork, recent_days=180) -> None:
        self._provider = provider
        self._uow = uow
        self.recent_days = recent_days
        from edgar import set_identity

        set_identity("user@exampe.com")

    async def run(self, report_requested: ReportRequested) -> InsiderReport | None:
        today = datetime.today()
        start_date = (today - dt.timedelta(days=self.recent_days)).date()
        end_date = datetime.today().date()

        with cast(Any, self._uow) as uow:
            report_request_repository: ReportRequestRepository = uow.repository(cast(Any, ReportRequestRepository))
            report_request: ReportRequest | None = report_request_repository.get_by_id(report_requested.report_id)
            if report_request is None:
                logger.error("Report request not found: %s", report_requested.report_id)
                return None
            try:
                transactions, provenance = self._provider.fetch_transactions(
                    ticker=report_requested.ticker, start_date=start_date, end_date=end_date
                )
                if transactions is None:
                    report_request.mark_as_failed(FailureContext.from_exception(
                        ValueError(f"No insider events returned for ticker '{report_request.ticker}' "
                                   f"(report_id={report_request.id}, as_of={report_request.as_of}, ")))
                    report_request_repository.add(report_request)
                    return None
                insider_report: InsiderReport = InsiderReport.create(
                    report_id=report_requested.report_id,
                    transactions=transactions,
                    period_start=start_date,
                    period_end=end_date,
                    provenance=provenance,
                )
                uow.repository(cast(Any, ReportPayloadRepository)).add(insider_report)
                return insider_report
            except Exception as e:
                logger.exception("Failed to generate insider report for %s", report_request.ticker)
                report_request.mark_as_failed(
                    FailureContext.from_exception(e)
                )
                report_request_repository.add(report_request)
                return None

        return None
