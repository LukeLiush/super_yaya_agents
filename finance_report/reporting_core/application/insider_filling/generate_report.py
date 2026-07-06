import datetime as dt
from datetime import datetime

from finance_report.reporting_core.application.insider_filling.provider import InsiderProvider
from finance_report.reporting_core.application.ports.report_repository import ReportPayloadRepository
from finance_report.reporting_core.application.ports.unit_of_work import UnitOfWork
from finance_report.reporting_core.application.use_cases.create_report_request import UseCase
from finance_report.reporting_core.domain.events import ReportRequested
from finance_report.reporting_core.domain.insider_report import InsiderReport


class GenerateInsiderReportUseCase(UseCase[ReportRequested, InsiderReport]):
    def __init__(self, provider: InsiderProvider, uow: UnitOfWork, recent_days=90) -> None:
        self._provider = provider
        self._uow = uow
        self.recent_days = recent_days
        from edgar import set_identity

        set_identity("user@exampe.com")

    async def run(self, report_requested: ReportRequested) -> InsiderReport:
        today = datetime.today()
        start_date = (today - dt.timedelta(days=self.recent_days)).date()
        end_date = datetime.today().date()

        transactions, provenance = self._provider.fetch_transactions(
            ticker=report_requested.ticker, start_date=start_date, end_date=end_date
        )
        insider_report: InsiderReport = InsiderReport.create(
            ticker=report_requested.ticker,
            report_id=report_requested.report_id,
            transactions=transactions,
            period_start=start_date,
            period_end=end_date,
            provenance=provenance,
        )
        with self._uow as uow:
            uow.repository(ReportPayloadRepository).save(insider_report)
        return insider_report
