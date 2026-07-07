from typing import Any, cast

import inngest
import yfinance as yf
from agno.models.dashscope import DashScope
from agno.tools.slack import SlackTools
from inngest import PydanticSerializer
from lagom import Container, Singleton
from tenacity import Retrying, stop_after_attempt, wait_exponential

from finance_report.reporting_core.application.insider_filling.generate_report import GenerateInsiderReportUseCase
from finance_report.reporting_core.application.insider_filling.provider import InsiderProvider
from finance_report.reporting_core.application.market_data.generate_report import GeneratePriceReportUseCase
from finance_report.reporting_core.application.market_data.provider import MarketDataProvider, SplitProvider
from finance_report.reporting_core.application.news.generate_report import GenerateNewsReportUseCase
from finance_report.reporting_core.application.news.provider import NewsProvider
from finance_report.reporting_core.application.ports.company_snapshot_provider import CompanySnapshotProvider
from finance_report.reporting_core.application.ports.report_notification import ReportNotifier
from finance_report.reporting_core.application.ports.report_repository import (
    ReportPayloadRepository,
    ReportRequestRepository,
)
from finance_report.reporting_core.application.ports.report_summarization import ReportSummarizer
from finance_report.reporting_core.application.ports.unit_of_work import UnitOfWork
from finance_report.reporting_core.application.use_cases.create_report_request import CreateReportRequestUseCase
from finance_report.reporting_core.domain.price_report import Window
from finance_report.reporting_core.infrastructure.adapters.agno_report_transformation_adapter import (
    AgnoReportSummarizer,
)
from finance_report.reporting_core.infrastructure.adapters.edgar_insider_adapter import EdgarInsiderAdapter
from finance_report.reporting_core.infrastructure.adapters.slack_report_notification import SlackReportNotifier
from finance_report.reporting_core.infrastructure.adapters.yfinance_company_snapshot_provider import (
    YFinanceCompanySnapshotProvider,
)
from finance_report.reporting_core.infrastructure.adapters.yfinance_news_adapter import YfinanceNewsAdapter
from finance_report.reporting_core.infrastructure.adapters.yfinance_price_adapter import (
    YFinanceMarketDataAdapter,
    YFinanceSplitAdapter,
)
from finance_report.reporting_core.infrastructure.config.report_usecase_registry import ReportRegistry
from finance_report.reporting_core.infrastructure.config.settings import settings
from finance_report.reporting_core.infrastructure.flows.inngest_finance_report_service import (
    InngestFinanceReportService,
)
from finance_report.reporting_core.infrastructure.persistence.sqlite_report_payload_repo import (
    SqliteReportPayloadRepository,
)
from finance_report.reporting_core.infrastructure.persistence.sqlite_report_request_repo import (
    SqliteReportRequestRepository,
)
from finance_report.reporting_core.infrastructure.persistence.sqlite_uow import SqliteUnitOfWork
from finance_report.reporting_core.infrastructure.web.asgi_adapter import ASGIAdapter
from finance_report.reporting_core.infrastructure.web.inngest_asgi import InngestASGI
from finance_report.reporting_core.infrastructure.web.prefect_asgi import PrefectASGI

container: Container = Container()

# 1. Bind Repository as a Singleton (shared DB connection)
# ponytail: db path could be injected from env
container[cast(Any, UnitOfWork)] = Singleton(
    lambda: SqliteUnitOfWork(
        db_path="finance_reports.db",
        repository_factories={
            ReportRequestRepository: SqliteReportRequestRepository,
            ReportPayloadRepository: SqliteReportPayloadRepository,
        },
    )
)

# 2. Bind Adapters
# ponytail: YFinanceAdapter has a complex constructor (Retrying), so we bind it explicitly
container[Retrying] = Retrying(
    stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True
)

WINDOWS = [
    Window.one_day(),
    Window.one_week(),
    Window.one_month(),
    Window.three_month(),
    Window.one_year(),
]
container[cast(Any, MarketDataProvider)] = Singleton(
    YFinanceMarketDataAdapter(retrying=container[Retrying], windows=WINDOWS)
)

_inngest_client = inngest.Inngest(
    app_id="finance-report-app", is_production=settings.is_production, serializer=PydanticSerializer()
)

container[inngest.Inngest] = Singleton(_inngest_client)
container[cast(Any, SplitProvider)] = Singleton(YFinanceSplitAdapter(container[Retrying]))
container[cast(Any, NewsProvider)] = Singleton(YfinanceNewsAdapter(container[Retrying]))
container[cast(Any, InsiderProvider)] = Singleton(EdgarInsiderAdapter())

SLACK_FORMAT = (
    "Format the output as Slack mrkdwn (NOT standard Markdown): "
    "*bold* with single asterisks, _italics_ with underscores, "
    "• for bullets, no # / ## / ### headers, links as <url|text>. "
    "Keep under ~2500 characters."
)
container[cast(Any, ReportSummarizer)] = Singleton(
    AgnoReportSummarizer.from_model(
        DashScope(id="qwen-plus", api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url),
        instructions=SLACK_FORMAT,
    )
)
container[cast(Any, CompanySnapshotProvider)] = Singleton(
    lambda: YFinanceCompanySnapshotProvider(ticker_factory=lambda s: yf.Ticker(s))
)
container[cast(Any, ReportNotifier)] = Singleton(
    SlackReportNotifier(
        SlackTools(settings.slack_bot_token),
        settings.slack_channel_id,
    )
)

# Use cases are resolved automatically by type hints if dependencies are bound
container[CreateReportRequestUseCase] = Singleton(
    lambda: CreateReportRequestUseCase(container[cast(Any, SplitProvider)], container[cast(Any, UnitOfWork)])
)
container[GeneratePriceReportUseCase] = Singleton(
    lambda: GeneratePriceReportUseCase(
        container[cast(Any, MarketDataProvider)], container[cast(Any, UnitOfWork)], WINDOWS
    )
)
container[GenerateNewsReportUseCase] = Singleton(
    lambda: GenerateNewsReportUseCase(
        container[cast(Any, NewsProvider)],
        container[cast(Any, UnitOfWork)],
    )
)
container[GenerateInsiderReportUseCase] = Singleton(
    lambda: GenerateInsiderReportUseCase(
        container[cast(Any, InsiderProvider)], container[cast(Any, UnitOfWork)], recent_days=90
    )
)
container[ReportRegistry] = Singleton(ReportRegistry(container))
container[InngestFinanceReportService] = Singleton(
    lambda: InngestFinanceReportService(
        create_request_use_case=container[CreateReportRequestUseCase],
        company_snapshot_provider=container[cast(Any, CompanySnapshotProvider)],
        report_notifier=container[cast(Any, ReportNotifier)],
        summarizer=container[cast(Any, ReportSummarizer)],
        report_registry=container[ReportRegistry],
    )
)


if settings.inngest_enabled:
    container[cast(Any, ASGIAdapter)] = Singleton(
        lambda: InngestASGI(
            inngest_finance_report_service=container[InngestFinanceReportService],
            inngest_client=container[inngest.Inngest],
        )
    )
else:
    container[cast(Any, ASGIAdapter)] = Singleton(lambda: PrefectASGI())
