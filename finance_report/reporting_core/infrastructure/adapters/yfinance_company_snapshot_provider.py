from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable, Optional
from typing import Protocol

import yfinance as yf

from ...application.ports.company_snapshot_provider import CompanySnapshotProvider, CompanySnapshot
from ...domain.shared_values import Ticker


class CompanyInfoUnavailable(RuntimeError):
    """Raised when yfinance returns no usable data for a ticker."""


class QuoteHandle(Protocol):
    @property
    def fast_info(self): ...

    @property
    def info(self) -> dict: ...


class YFinanceCompanySnapshotProvider(CompanySnapshotProvider):
    def __init__(self, ticker_factory: Optional[Callable[[str], QuoteHandle]] = None):
        self._make = ticker_factory or (lambda s: yf.Ticker(s))

    async def fetch(self, ticker: Ticker) -> CompanySnapshot:
        return await asyncio.to_thread(self._fetch_sync, ticker)

    def _fetch_sync(self, ticker: Ticker) -> CompanySnapshot:
        symbol = ticker.symbol
        yf_ticker = self._make(symbol)
        return CompanySnapshot(
            name=self._resolve_name(yf_ticker, symbol),
            ticker=ticker,
            last_price=self._resolve_price(yf_ticker, symbol),
            fetched_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _resolve_price(yf_ticker: QuoteHandle, symbol: str) -> Decimal:
        try:
            last = yf_ticker.fast_info.last_price
            if last is not None:
                return Decimal(str(last))
        except Exception:
            pass
        try:
            prev = yf_ticker.fast_info.previous_close
            if prev is not None:
                return Decimal(str(prev))
        except Exception:
            pass
        raise CompanyInfoUnavailable(f"No price available for {symbol}")

    @staticmethod
    def _resolve_name(yf_ticker: QuoteHandle, symbol: str) -> str:
        try:
            info = yf_ticker.info or {}
            name = info.get("longName") or info.get("shortName")
            if name:
                return name
        except Exception:
            pass
        return symbol
