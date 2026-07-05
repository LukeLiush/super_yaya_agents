from typing import Tuple, Protocol, Optional

from finance_report.reporting_core.domain.price_report import DailyPriceBar
from finance_report.reporting_core.domain.shared_values import Ticker, SplitEvent, Provenance


class MarketDataProvider(Protocol):
    def fetch_prices(self, ticker: Ticker) -> Tuple[Tuple[DailyPriceBar, ...], Optional[Provenance]]:
        ...


class SplitProvider(Protocol):
    def fetch_latest_splits(self, ticker: Ticker) -> Optional[SplitEvent]:
        ...
