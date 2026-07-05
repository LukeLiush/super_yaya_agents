from typing import Protocol, Tuple, Optional

from finance_report.reporting_core.application.news.dtos import NewsItem
from finance_report.reporting_core.domain.shared_values import Ticker, Provenance


class NewsProvider(Protocol):
    def fetch_latest_news(self, ticker: Ticker) -> Tuple[list[NewsItem], Optional[Provenance]]:
        ...
