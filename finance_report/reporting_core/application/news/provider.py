from typing import Protocol, Tuple, Optional

from .dtos import NewsItem
from ...domain.shared_values import Ticker, Provenance


class NewsProvider(Protocol):
    def fetch_latest_news(self, ticker: Ticker) -> Tuple[list[NewsItem], Optional[Provenance]]:
        ...
