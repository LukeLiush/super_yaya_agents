import asyncio
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
from finance_report.reporting_core.infrastructure.config.settings import Settings, get_settings
from finance_report.reporting_core.infrastructure.flows.inngest_finance_report_service import (
    InngestFinanceReportService,
)
from finance_report.reporting_core.infrastructure.persistence.sqlite_report_payload_repo import \
    SqliteReportPayloadRepository
from finance_report.reporting_core.infrastructure.persistence.sqlite_report_request_repo import \
    SqliteReportRequestRepository
from finance_report.reporting_core.infrastructure.persistence.sqlite_uow import SqliteUnitOfWork
from finance_report.reporting_core.infrastructure.web.asgi_adapter import ASGIAdapter
from finance_report.reporting_core.infrastructure.web.inngest_asgi import InngestASGI
from finance_report.reporting_core.infrastructure.web.prefect_asgi import PrefectASGI

_container: Container | None = None
_lock = asyncio.Lock()


async def get_container() -> Container:
    settings: Settings = await get_settings()
    global _container
    if _container is not None:
        return _container
    async with _lock:
        if _container is not None:
            return _container
        _container = _build(settings)
        return _container


def _build(settings: Settings) -> Container:
    the_container: Container = Container()
    # 1. Bind Repository as a Singleton (shared DB connection)
    # ponytail: db path could be injected from env
    the_container[cast(Any, UnitOfWork)] = \
        lambda: SqliteUnitOfWork(
            db_path="finance_reports.db",
            repository_factories={
                ReportRequestRepository: SqliteReportRequestRepository,
                ReportPayloadRepository: SqliteReportPayloadRepository,
            },
        )


    # 2. Bind Adapters
    # ponytail: YFinanceAdapter has a complex constructor (Retrying), so we bind it explicitly
    the_container[Retrying] = Retrying(
        stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True
    )

    WINDOWS = [
        Window.one_day(),
        Window.one_week(),
        Window.one_month(),
        Window.three_month(),
        Window.one_year(),
    ]
    the_container[cast(Any, MarketDataProvider)] = Singleton(
        YFinanceMarketDataAdapter(retrying=the_container[Retrying], windows=WINDOWS)
    )

    _inngest_client = inngest.Inngest(
        app_id="finance-report-app", is_production=settings.is_production, serializer=PydanticSerializer()
    )

    the_container[inngest.Inngest] = Singleton(_inngest_client)
    the_container[cast(Any, SplitProvider)] = Singleton(YFinanceSplitAdapter(the_container[Retrying]))
    the_container[cast(Any, NewsProvider)] = Singleton(YfinanceNewsAdapter(the_container[Retrying]))
    the_container[cast(Any, InsiderProvider)] = Singleton(EdgarInsiderAdapter())

    SLACK_FORMAT = (
        "Format the output as Slack mrkdwn (NOT standard Markdown): "
        "*bold* with single asterisks, _italics_ with underscores, "
        "• for bullets, no # / ## / ### headers, links as <url|text>. "
        "Keep under ~2500 characters."
    )
    the_container[cast(Any, ReportSummarizer)] = Singleton(lambda:
                                                           AgnoReportSummarizer.from_model(
                                                               DashScope(id="qwen-plus",
                                                                         api_key=settings.dashscope_api_key,
                                                                         base_url=settings.dashscope_base_url),
                                                               instructions=SLACK_FORMAT,
                                                           )
                                                           )
    the_container[cast(Any, CompanySnapshotProvider)] = Singleton(
        lambda: YFinanceCompanySnapshotProvider(ticker_factory=lambda s: yf.Ticker(s))
    )
    the_container[cast(Any, ReportNotifier)] = Singleton(lambda:
                                                         SlackReportNotifier(
                                                             SlackTools(settings.slack_bot_token),
                                                             settings.slack_channel_id,
                                                         )
                                                         )

    # Use cases are resolved automatically by type hints if dependencies are bound
    the_container[CreateReportRequestUseCase] = Singleton(
        lambda: CreateReportRequestUseCase(the_container[cast(Any, SplitProvider)],
                                           the_container[cast(Any, UnitOfWork)])
    )
    the_container[GeneratePriceReportUseCase] = Singleton(
        lambda: GeneratePriceReportUseCase(
            the_container[cast(Any, MarketDataProvider)], the_container[cast(Any, UnitOfWork)], WINDOWS
        )
    )
    the_container[GenerateNewsReportUseCase] = Singleton(
        lambda: GenerateNewsReportUseCase(
            the_container[cast(Any, NewsProvider)],
            the_container[cast(Any, UnitOfWork)],
        )
    )
    the_container[GenerateInsiderReportUseCase] = Singleton(
        lambda: GenerateInsiderReportUseCase(
            the_container[cast(Any, InsiderProvider)], the_container[cast(Any, UnitOfWork)]
        )
    )
    the_container[ReportRegistry] = Singleton(lambda: ReportRegistry(the_container))
    the_container[InngestFinanceReportService] = Singleton(
        lambda: InngestFinanceReportService(
            create_request_use_case=the_container[CreateReportRequestUseCase],
            company_snapshot_provider=the_container[cast(Any, CompanySnapshotProvider)],
            report_notifier=the_container[cast(Any, ReportNotifier)],
            summarizer=the_container[cast(Any, ReportSummarizer)],
            report_registry=the_container[ReportRegistry],
        )
    )

    if settings.inngest_enabled:
        the_container[cast(Any, ASGIAdapter)] = Singleton(
            lambda: InngestASGI(
                inngest_finance_report_service=the_container[InngestFinanceReportService],
                inngest_client=the_container[inngest.Inngest],
            )
        )
    else:
        the_container[cast(Any, ASGIAdapter)] = Singleton(lambda: PrefectASGI())
    return the_container
