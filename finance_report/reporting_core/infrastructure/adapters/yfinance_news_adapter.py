import logging
from datetime import UTC, datetime

import yfinance as yf
from pydantic import BaseModel, ConfigDict, field_validator
from tenacity import Retrying, before_sleep_log, stop_after_attempt, wait_exponential

from finance_report.reporting_core.application.news.dtos import NewsItem
from finance_report.reporting_core.application.news.provider import NewsProvider
from finance_report.reporting_core.domain.shared_values import Provenance, Ticker

logger = logging.getLogger(__name__)


# --- Models mirroring yfinance's raw shape (only the fields we need) ---
class _YFProvider(BaseModel):
    model_config = ConfigDict(extra="ignore")
    displayName: str | None = None


class _YFUrl(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str | None = None


class _YFContent(BaseModel):
    model_config = ConfigDict(extra="ignore")  # tolerate the many fields we don't use
    title: str | None = None
    summary: str | None = None
    pubDate: datetime | None = None
    displayTime: datetime | None = None
    provider: _YFProvider | None = None
    canonicalUrl: _YFUrl | None = None
    clickThroughUrl: _YFUrl | None = None

    @field_validator("pubDate", "displayTime", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        if v == "" or v is None:
            return None
        return v


class _YFNewsRaw(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str | None = None
    content: _YFContent | None = None

    @staticmethod
    def from_raw(raw: dict) -> "_YFNewsRaw":
        parsed: _YFNewsRaw = _YFNewsRaw.model_validate(raw)
        return parsed

    def to_news_item(self) -> NewsItem | None:
        c = self.content
        if c is None:
            return None

        url = (c.canonicalUrl.url if c.canonicalUrl and c.canonicalUrl.url else None) or (
            c.clickThroughUrl.url if c.clickThroughUrl and c.clickThroughUrl.url else None
        )
        published_at = c.pubDate or c.displayTime
        publisher = c.provider.displayName if c.provider else None

        # Required fields on NewsItem — skip items missing the essentials
        if not (c.title and url and publisher and published_at):
            return None

        return NewsItem(
            headline=c.title,
            url=url,
            publisher=publisher,
            published_at=published_at,
            summary=c.summary or None,
        )


class YfinanceNewsAdapter(NewsProvider):
    def __init__(self, retrying: Retrying | None = None, count_of_news=10):
        self._retrying = retrying or Retrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
            before_sleep=before_sleep_log(logger, logging.INFO),
        )
        self._count_of_news = count_of_news

    def _fetch(
        self,
        symbol: str,
    ) -> tuple[list, Provenance]:
        raws: list = yf.Ticker(symbol).get_news(count=self._count_of_news, tab="news")
        if raws is None or len(raws) == 0:
            raise ValueError(f"Yfinance returned no news for {symbol}")
        provenance = Provenance(
            source=yf.__name__,
            query=f'yf.Ticker("{symbol}").get_news("{self._count_of_news}")',
            queried_at=datetime.now(UTC),
            source_version=yf.__version__,
        )
        return raws, provenance

    def fetch_latest_news(self, ticker: Ticker) -> tuple[list[NewsItem], Provenance | None]:
        raws, provenance = self._retrying(self._fetch, ticker.symbol)
        news_items = []
        for raw in raws:
            try:
                item = _YFNewsRaw.from_raw(raw).to_news_item()
                if item is not None:
                    news_items.append(item)
            except Exception:
                logger.exception("Failed to parse news item; raw=%s", raw)
                # skip the bad item, keep going

        return news_items, provenance
