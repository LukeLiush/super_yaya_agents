import logging
from datetime import timezone, datetime
from decimal import Decimal
from typing import Optional, Tuple, List

import pandas as pd
import yfinance as yf
from tenacity import Retrying, stop_after_attempt, wait_exponential

from finance_report.reporting_core.application.market_data.provider import MarketDataProvider, SplitProvider
from finance_report.reporting_core.domain.price_report import PriceReport, Window, DailyPriceBar
from finance_report.reporting_core.domain.shared_values import Ticker, SplitEvent, Provenance

logger = logging.getLogger(__name__)


class YFinanceSplitAdapter(SplitProvider):
    """Infrastructure adapter for fetching split events using yfinance."""

    def __init__(self, retrying: Optional[Retrying] = None):
        self._retrying = retrying or Retrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )

    @staticmethod
    def _fetch_splits_with_provenance(symbol: str) -> Tuple[pd.Series, Provenance]:
        """Internal method to fetch splits from yfinance."""
        ticker = yf.Ticker(symbol)
        splits: pd.Series = ticker.splits
        provenance = Provenance(source=yf.__name__,
                                query=f"yf.Ticker(\"{symbol}\").splits",
                                queried_at=datetime.now(timezone.utc),
                                source_version=yf.__version__)
        return splits, provenance

    def fetch_latest_splits(self, ticker: Ticker) -> Optional[SplitEvent]:
        try:
            # 1. Fetch splits (returns a pandas Series)
            splits, provenance = self._retrying(self._fetch_splits_with_provenance, ticker.symbol)

            if splits.empty:
                return None

            # 2. Get the most recent split event
            # yfinance returns splits sorted by date ascending
            latest_date = splits.index[-1]
            ratio = splits.iloc[-1]

            return SplitEvent(
                ex_date=latest_date.date(),
                ratio=Decimal(str(ratio)), provenance=provenance
            )
        except:
            # ponytail: use logger.exception to capture stack trace automatically
            logger.error(f"Failed to fetch splits for {ticker.symbol}", exc_info=True)
            return None


class YFinanceMarketDataAdapter(MarketDataProvider):
    """Infrastructure adapter for yfinance."""

    def __init__(self, windows: List[Window], retrying: Optional[Retrying] = None, ):
        self.windows = windows
        self._retrying = retrying or Retrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True
        )
        self.provenance: Provenance | None = None

    @staticmethod
    def _fetch_with_provenance(symbol: str, period: str, interval: str = "1d") -> Tuple[pd.DataFrame, Provenance]:
        logger.info(f"Fetching yfinance history for {symbol}")
        ticker = yf.Ticker(symbol)

        df = ticker.history(period=period, interval=interval)

        provenance = Provenance(source=yf.__name__,
                                query=f"yf.Ticker(\"{symbol}\").history(period=\"{period}\", interval=\"{interval}\")",
                                queried_at=datetime.now(timezone.utc),
                                source_version=yf.__version__)
        return df, provenance

    def fetch_prices(self, ticker: Ticker) -> Tuple[Tuple[DailyPriceBar, ...], Optional[Provenance]]:
        max_days = max(PriceReport.window_to_days(window) for window in self.windows)
        """
        yfinance supported history period argumnents
        •1d: 1 Day
        •5d: 5 Days
        •1mo: 1 Month
        •3mo: 3 Months
        •6mo: 6 Months
        •1y: 1 Year
        •2y: 2 Years
        •5y: 5 Years
        •10y: 10 Years
        •ytd: Year to Date
        •max: All available data
       """
        if max_days <= 5:
            yf_period = "5d"
        elif max_days <= 30:
            yf_period = "1mo"
        elif max_days <= 90:
            yf_period = "3mo"
        elif max_days <= 180:
            yf_period = "6mo"
        elif max_days <= 365:
            yf_period = "1y"
        elif max_days <= 730:
            yf_period = "2y"
        elif max_days <= 1825:
            yf_period = "5y"
        elif max_days <= 3650:
            yf_period = "10y"
        else:
            yf_period = "max"
        try:
            df, provenance = self._retrying(self._fetch_with_provenance, ticker.symbol, yf_period)
            bars: List[DailyPriceBar] = []
            for index, row in df.iterrows():
                bars.append(DailyPriceBar(
                    date=index.date(),
                    open=Decimal(str(row["Open"])),
                    high=Decimal(str(row["High"])),
                    low=Decimal(str(row["Low"])),
                    close=Decimal(str(row["Close"])),
                    volume=int(row["Volume"])
                ))
            return tuple(bars), provenance
        except:
            logger.error(f"Failed to generate report for {ticker.symbol}", exc_info=True)  # ERROR + traceback
            return (), None
