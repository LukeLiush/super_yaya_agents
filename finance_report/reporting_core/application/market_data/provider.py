from typing import Protocol

from finance_report.reporting_core.domain.price_report import DailyPriceBar
from finance_report.reporting_core.domain.shared_values import Provenance, SplitEvent, Ticker


class MarketDataProvider(Protocol):
    def fetch_prices(self, ticker: Ticker) -> tuple[tuple[DailyPriceBar, ...], Provenance | None]: ...


class SplitProvider(Protocol):
    def fetch_latest_splits(self, ticker: Ticker) -> SplitEvent | None: ...
