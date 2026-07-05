from datetime import datetime
from decimal import Decimal
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from finance_report.reporting_core.domain.shared_values import Ticker


class CompanySnapshot(BaseModel):  # or keep CompanyInfo
    model_config = ConfigDict(frozen=True)
    name: str
    ticker: Ticker
    last_price: Decimal  # Decimal for consistency with PriceReport
    fetched_at: datetime


class CompanySnapshotProvider(Protocol):
    async def fetch(self, ticker: Ticker) -> CompanySnapshot: ...
