import datetime
import logging
from decimal import Decimal
from typing import List
from zoneinfo import ZoneInfo

import inngest.fast_api
from inngest._internal import server_lib
from pydantic import BaseModel

from finance_report.finance_sdk.schemas import ReportTriggerRequest, ReportType
from finance_report.reporting_core.application.ports.company_snapshot_provider import CompanySnapshotProvider, \
    CompanySnapshot
from finance_report.reporting_core.application.ports.report_notification import ReportNotifier, NotificationThread
from finance_report.reporting_core.application.ports.report_summarization import ReportSummarizer
from finance_report.reporting_core.application.use_cases.create_report_request import CreateReportRequestUseCase, \
    CreateRequestInput
from finance_report.reporting_core.domain.events import ReportRequested
from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.domain.shared_values import Ticker, ReportPayload
from finance_report.reporting_core.infrastructure.config.report_usecase_registry import ReportRegistry, ReportHandler

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class ReportRunResult(BaseModel):
    ticker: str
    report_types: list[str]
    thread_ref: str | None
    summaries: dict[str, str]  # report_type -> summary


class InngestFinanceReportService:

    def __init__(
            self,
            report_registry: ReportRegistry,
            create_request_use_case: CreateReportRequestUseCase,
            company_snapshot_provider: CompanySnapshotProvider,
            report_notifier: ReportNotifier,
            summarizer: ReportSummarizer,
    ) -> None:
        self._report_registry: ReportRegistry = report_registry
        self._create_request_use_case = create_request_use_case
        self._company_snapshot_provider = company_snapshot_provider
        self._report_notifier = report_notifier
        self._summarizer = summarizer

    async def run_report_generation(
            self,
            report_trigger_request: ReportTriggerRequest,
            ctx: inngest.Context,
    ) -> ReportRunResult:
        ticker_symbol = report_trigger_request.ticker
        report_types: List[ReportType] = report_trigger_request.report_types
        step = ctx.step

        async def submit_report_request(_report_type: str) -> ReportRequested:
            logger.info("Report request for ticker=%s", ticker_symbol)
            report_request: ReportRequest = await self._create_request_use_case.run(
                CreateRequestInput(ticker=Ticker(symbol=ticker_symbol), requested_by="shua@")
            )
            return report_request.report_requested()

        report_requested: ReportRequested = await step.run(
            "submit-report-request",
            submit_report_request,
            "price-report",
            output_type=ReportRequested,
        )

        company_snapshot: CompanySnapshot = await step.run(
            "fetching_company_snapshot",
            self._company_snapshot_provider.fetch,
            report_requested.ticker,
            output_type=CompanySnapshot,
        )

        subject = self._create_attractive_subject(
            ticker=report_requested.ticker,
            company_info=company_snapshot.name,
            current_price=company_snapshot.last_price,
        )

        notification_thread: NotificationThread = await step.run(
            "creating_slack_thread",
            self._report_notifier.open_thread,
            subject,
            output_type=NotificationThread,
        )

        results = await ctx.group.parallel(
            tuple(
                self._make_thunk(step, rt, report_requested, notification_thread)
                for rt in report_types
            ),
            parallel_mode=server_lib.ParallelMode.RACE,
        )

        return ReportRunResult(
            ticker=report_requested.ticker.symbol,
            report_types=report_types,
            thread_ref=notification_thread.ref,
            summaries=dict(zip(report_types, results)),
        )

    def _make_thunk(self, step, report_type: ReportType,
                    report_requested: ReportRequested,
                    notification_thread: NotificationThread):
        handler: ReportHandler = self._report_registry.handler_for(report_type)

        async def report_pipeline():
            report: ReportPayload = await step.run(
                f"{report_type}-report",
                handler.run,
                report_requested,
                output_type=handler.return_type,
            )
            summary: str = await step.run(
                f"{report_type}-summarize",
                self._summarizer.summarize,
                report,
            )
            await step.run(
                f"{report_type}-slack-notify",
                self._report_notifier.post_report,
                notification_thread,
                summary,
                output_type=None,
            )
            return summary

        return report_pipeline

    @staticmethod
    def _create_attractive_subject(ticker: Ticker, company_info: str,
                                   current_price: Decimal) -> str:
        pst_time = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
        date_str = pst_time.strftime("%B %d, %Y")
        return (
            f"🚀 *DAILY EQUITY INTELLIGENCE BRIEF* | {date_str}\n"
            f"Targeting: *{company_info}* (`{ticker}`) | Current Price: *${current_price:,.2f}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Greetings! 👋 I'm diving deep into the markets for the latest price "
            f"action, insider moves, and breaking news on *{company_info}*. "
            f"Hang tight! 📈💎🙌"
        )
