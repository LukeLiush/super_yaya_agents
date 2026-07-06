from typing import Protocol

from finance_report.reporting_core.application.news.dtos import NewsItem
from finance_report.reporting_core.domain.shared_values import Provenance, Ticker


class NewsProvider(Protocol):
    def fetch_latest_news(self, ticker: Ticker) -> tuple[list[NewsItem], Provenance | None]: ...
