import asyncio
import datetime
import logging
from decimal import Decimal
from typing import Any, cast
from zoneinfo import ZoneInfo

from prefect import flow, task

from finance_report.finance_sdk.schemas import ReportTriggerRequest, ReportType
from finance_report.reporting_core.application.ports.company_snapshot_provider import (
    CompanySnapshot,
    CompanySnapshotProvider,
)
from finance_report.reporting_core.application.ports.report_notification import NotificationThread, ReportNotifier
from finance_report.reporting_core.application.ports.report_summarization import ReportSummarizer
from finance_report.reporting_core.application.use_cases.create_report_request import (
    CreateReportRequestUseCase,
    CreateRequestInput,
)
from finance_report.reporting_core.domain.events import ReportRequested
from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.domain.shared_values import ReportPayload, Ticker
from finance_report.reporting_core.infrastructure.config.report_usecase_registry import ReportHandler, ReportRegistry
from finance_report.reporting_core.infrastructure.flows.inngest_finance_report_service import ReportRunResult
from finance_report.reporting_core.infrastructure.flows.prefect_utils import run_name_from

logger = logging.getLogger(__name__)


@task(name="submit_report_request", retries=3)
async def _submit_report_request(
    ticker: Ticker,
    requested_by: str,
) -> ReportRequested:
    logger.info("Report request for ticker=%s", ticker.symbol)
    from finance_report.reporting_core.infrastructure.config.container import container

    create_request_use_case: CreateReportRequestUseCase = container[CreateReportRequestUseCase]
    report_request: ReportRequest = await create_request_use_case.run(
        CreateRequestInput(ticker=Ticker(symbol=ticker.symbol), requested_by=requested_by)
    )
    return report_request.report_requested()


@task(name="fetch_snapshot", retries=3)
async def _fetch_snapshot(
    ticker: Ticker,
) -> CompanySnapshot:
    from typing import Any

    from finance_report.reporting_core.infrastructure.config.container import container

    company_snapshot_provider: CompanySnapshotProvider = container[cast(Any, CompanySnapshotProvider)]
    snapshot: CompanySnapshot = await company_snapshot_provider.fetch(ticker)
    return snapshot


@task(name="open_slack_thread", retries=3)
async def _open_slack_thread(
    subject: str,
) -> NotificationThread:
    from typing import Any

    from finance_report.reporting_core.infrastructure.config.container import container

    report_notifier: ReportNotifier = container[cast(Any, ReportNotifier)]
    res = await report_notifier.open_thread(subject)
    if res is None:
        raise ValueError("Failed to open Slack thread")
    return res


@task(name="post_slack_message", retries=3)
async def _post_slack_message(
    thread: NotificationThread,
    report: str,
) -> None:
    from typing import Any

    from finance_report.reporting_core.infrastructure.config.container import container

    report_notifier: ReportNotifier = container[cast(Any, ReportNotifier)]
    await report_notifier.post_report(thread, report)


@task(
    task_run_name=run_name_from(
        lambda p: f"[{p['report_requested'].ticker}] {p['report_type']}", prefix="run_report_pipeline"
    ),
    retries=3,
)
async def _run_report_pipeline(
    report_requested: ReportRequested,
    report_type: ReportType,
    thread: NotificationThread,
) -> str:
    from typing import Any

    from finance_report.reporting_core.infrastructure.config.container import container

    report_registry: ReportRegistry = container[ReportRegistry]
    summarizer: ReportSummarizer = container[cast(Any, ReportSummarizer)]
    logger.info("Running report pipeline for %s", report_requested.report_id)
    report_handler: ReportHandler = report_registry.handler_for(report_type)
    report_payload: ReportPayload | None = await report_handler.run(report_requested)
    if report_payload is None:
        return "No data for this report"
    summary: str = await summarizer.summarize(report_payload)
    await _post_slack_message(thread, summary)
    return summary


@flow(log_prints=True)
async def finance_report_flow(report_trigger_request: ReportTriggerRequest, requested_by: str) -> ReportRunResult:
    ticker: Ticker = Ticker(symbol=report_trigger_request.ticker)
    report_types = list(dict.fromkeys(report_trigger_request.report_types))

    report_requested: ReportRequested = await _submit_report_request(
        ticker,
        requested_by,
    )

    snapshot: CompanySnapshot = await _fetch_snapshot(report_requested.ticker)
    subject = _create_attractive_subject(
        ticker=report_requested.ticker,
        company_info=snapshot.name,
        current_price=snapshot.last_price,
    )
    thread: NotificationThread = await _open_slack_thread(subject)

    # Fan-out: submit all per-report pipelines concurrently.
    futures = [
        _run_report_pipeline.submit(
            report_requested,
            report_type,
            thread,
        )
        for report_type in report_types
    ]
    # In Prefect, .result() on a future returns the result directly.
    # If the flow is async, we may need to handle it.
    summaries: list[str] = []
    for future in futures:
        # res can be str or Coroutine[Any, Any, str]
        res: Any = future.result()
        if asyncio.iscoroutine(res):
            res = await res
        summaries.append(str(res))

    return ReportRunResult(
        ticker=report_requested.ticker.symbol,
        report_types=[str(report_type) for report_type in report_types],
        thread_ref=thread.ref,
        summaries={str(rt): s for rt, s in zip(report_types, summaries, strict=True)},
    )


def _create_attractive_subject(ticker: Ticker, company_info: str, current_price: Decimal) -> str:
    pst_time = datetime.datetime.now(ZoneInfo("America/Los_Angeles"))
    date_str = pst_time.strftime("%B %d, %Y")
    return (
        f"🚀 *DAILY EQUITY INTELLIGENCE BRIEF* | {date_str}\n"
        f"Targeting: *{company_info}* (`{ticker.symbol}`) | Current Price: *${current_price:,.2f}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Greetings! 👋 I'm diving deep into the markets for the latest price "
        f"action, insider moves, and breaking news on *{company_info}*. "
        f"Hang tight! 📈💎🙌"
    )


if __name__ == "__main__":
    finance_report_flow.serve(name="my-deployment")
