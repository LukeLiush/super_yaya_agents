import logging
from typing import Dict

from agno.agent import Agent
from agno.models.base import Model

from ...application.ports.report_summarization import ReportSummarizer
from ...domain.insider_report import InsiderReport
from ...domain.news_report import NewsReport
from ...domain.price_report import PriceReport
from ...domain.shared_values import ReportPayload

logger = logging.getLogger(__name__)

FEW_SHOT: Dict[str, str] = {
    PriceReport.report_type(): (
        "Example output:\n"
        "*Price Ranges*\n"
        "```\n"
        "Period   High      Low\n"
        "1Day     432.10    398.81\n"
        "1Week    445.60    398.60\n"
        "1Month   445.60    368.60\n"
        "```\n"
    ),
    InsiderReport.report_type(): (
        "Example output:\n"
        "*Insider Transactions*\n"
        "```\n"
        "Date        Insider          Type   Shares    Price     Value\n"
        "2026-06-28  J. Smith (CFO)   SELL   12,000    $392.00   $4.70M\n"
        "2026-06-20  A. Doe (Dir)     BUY     3,000    $400.00   $1.20M\n"
        "2026-06-15  R. Lee (CEO)     BUY     5,000    $388.00   $1.94M\n"
        "\n"
        "Totals\n"
        "  Bought:  8,000 shares   $3.14M\n"
        "  Sold:   12,000 shares   $4.70M\n"
        "  Net:    -4,000 shares  -$1.56M  (net selling)\n"
        "```\n"
    ),
    NewsReport.report_type(): (
        "*Recent News*\n"
        "• 🟢 *Bullish* — <https://example.com/a|Q2 deliveries beat estimates> (2026-06-30, Reuters)\n"
        "• 🔴 *Bearish* — <https://example.com/b|Regulatory probe opened in EU> (2026-06-28, Bloomberg)\n"
        "• ⚪ *Neutral* — <https://example.com/c|CEO to speak at conference> (2026-06-25, CNBC)\n"
    ),
}


class AgnoReportSummarizer(ReportSummarizer):
    _DEFAULT_INSTRUCTIONS = (
        "You are an equity research assistant. "
        "Given structured report data, produce a concise, factual summary "
        "of the key findings. Do not invent numbers not present in the input."
    )

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    async def summarize(self, report: ReportPayload) -> str:
        example: str = FEW_SHOT[report.report_type()]
        logger.info(f"here is my example: \n\n {example}")
        prompt = (
            f"Summarize this report. Emphasize: {report.summary_focus()}.\n\n"
            f"{example}\n"
            f"{report.to_prompt_context()}"
        )
        result = self._agent.run(prompt)
        return result.content

    @classmethod
    def from_model(cls, model: Model, *, instructions=None) -> "AgnoReportSummarizer":
        agent = Agent(model=model,
                      instructions=instructions or cls._DEFAULT_INSTRUCTIONS,
                      markdown=True)
        return cls(agent)
