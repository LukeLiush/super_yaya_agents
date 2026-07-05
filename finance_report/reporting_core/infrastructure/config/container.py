import inngest
import yfinance as yf
from agno.models.dashscope import DashScope
from agno.tools.slack import SlackTools
from inngest import PydanticSerializer
from lagom import Container, Singleton
from tenacity import Retrying, stop_after_attempt, wait_exponential

from .report_usecase_registry import ReportRegistry
from .settings import settings
from ..adapters.agno_report_transformation_adapter import AgnoReportSummarizer
from ..adapters.edgar_insider_adapter import EdgarInsiderAdapter
from ..adapters.slack_report_notification import SlackReportNotifier
from ..adapters.yfinance_company_snapshot_provider import YFinanceCompanySnapshotProvider
from ..adapters.yfinance_news_adapter import YfinanceNewsAdapter
from ..adapters.yfinance_price_adapter import YFinanceMarketDataAdapter, YFinanceSplitAdapter
from ..flows.inngest_finance_report_service import InngestFinanceReportService
from ..persistence.sqlite_report_payload_repo import SqliteReportPayloadRepository
from ..persistence.sqlite_report_request_repo import SqliteReportRequestRepository
from ..persistence.sqlite_uow import SqliteUnitOfWork
from ..web.asgi_adapter import ASGIAdapter
from ..web.inngest_asgi import InngestASGI
from ..web.prefect_asgi import PrefectASGI
from ...application.insider_filling.generate_report import GenerateInsiderReportUseCase
from ...application.insider_filling.provider import InsiderProvider
from ...application.market_data.generate_report import GeneratePriceReportUseCase
from ...application.market_data.provider import MarketDataProvider, SplitProvider
from ...application.news.generate_report import GenerateNewsReportUseCase
from ...application.news.provider import NewsProvider
from ...application.ports.company_snapshot_provider import CompanySnapshotProvider
from ...application.ports.report_notification import ReportNotifier
from ...application.ports.report_repository import ReportPayloadRepository, ReportRequestRepository
from ...application.ports.report_summarization import ReportSummarizer
from ...application.ports.unit_of_work import UnitOfWork
from ...application.use_cases.create_report_request import CreateReportRequestUseCase
from ...domain.price_report import Window

container: Container = Container()

# 1. Bind Repository as a Singleton (shared DB connection)
# ponytail: db path could be injected from env
container[UnitOfWork] = Singleton(SqliteUnitOfWork(db_path="finance_reports.db",
                                                   repository_factories= \
                                                       {
                                                           ReportRequestRepository: SqliteReportRequestRepository,
                                                           ReportPayloadRepository: SqliteReportPayloadRepository,
                                                       }
                                                   ))

# 2. Bind Adapters
# ponytail: YFinanceAdapter has a complex constructor (Retrying), so we bind it explicitly
container[Retrying] = Retrying(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)

WINDOWS = [
    Window.one_day(),
    Window.one_week(),
    Window.one_month(),
    Window.three_month(),
    Window.one_year(),
]
container[MarketDataProvider] = Singleton(YFinanceMarketDataAdapter(retrying=container[Retrying],
                                                                    windows=WINDOWS))

_inngest_client = inngest.Inngest(
    app_id="finance-report-app",
    is_production=settings.is_production,
    serializer=PydanticSerializer()
)

container[inngest.Inngest] = Singleton(_inngest_client)
container[SplitProvider] = Singleton(YFinanceSplitAdapter(container[Retrying]))
container[NewsProvider] = Singleton(YfinanceNewsAdapter(container[Retrying]))
container[InsiderProvider] = Singleton(EdgarInsiderAdapter())

SLACK_FORMAT = (
    "Format the output as Slack mrkdwn (NOT standard Markdown): "
    "*bold* with single asterisks, _italics_ with underscores, "
    "• for bullets, no # / ## / ### headers, links as <url|text>. "
    "Keep under ~2500 characters."
)
container[ReportSummarizer] = Singleton(AgnoReportSummarizer.from_model(
    DashScope(id="qwen-plus",
              api_key=settings.dashscope_api_key,
              base_url=settings.dashscope_base_url),
    instructions=SLACK_FORMAT)
)
container[CompanySnapshotProvider] = Singleton(
    lambda: YFinanceCompanySnapshotProvider(ticker_factory=lambda s: yf.Ticker(s)))
container[ReportNotifier] = Singleton(SlackReportNotifier(SlackTools(settings.slack_bot_token),
                                                          settings.slack_channel_id, ))

# Use cases are resolved automatically by type hints if dependencies are bound
container[CreateReportRequestUseCase] = Singleton(lambda: CreateReportRequestUseCase(container[SplitProvider],
                                                                                     container[UnitOfWork]))
container[GeneratePriceReportUseCase] = Singleton(lambda: GeneratePriceReportUseCase(container[MarketDataProvider],
                                                                                     container[UnitOfWork],
                                                                                     WINDOWS))
container[GenerateNewsReportUseCase] = Singleton(lambda: GenerateNewsReportUseCase(container[NewsProvider],
                                                                                   container[UnitOfWork], ))
container[GenerateInsiderReportUseCase] = Singleton(lambda: GenerateInsiderReportUseCase(container[InsiderProvider],
                                                                                         container[UnitOfWork],
                                                                                         recent_days=90))
container[ReportRegistry] = Singleton(ReportRegistry(container))
container[InngestFinanceReportService] = Singleton(lambda: InngestFinanceReportService(
    create_request_use_case=container[CreateReportRequestUseCase],
    company_snapshot_provider=container[CompanySnapshotProvider],
    report_notifier=container[ReportNotifier],
    summarizer=container[ReportSummarizer],
    report_registry=container[ReportRegistry],
))


if settings.inngest_enabled:
    container[ASGIAdapter] = Singleton(lambda: InngestASGI(
        inngest_finance_report_service=container[InngestFinanceReportService],
        inngest_client=container[inngest.Inngest]
    ))
else:
    container[ASGIAdapter] = Singleton(lambda: PrefectASGI())
