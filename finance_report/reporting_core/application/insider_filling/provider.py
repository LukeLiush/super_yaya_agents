from datetime import date
from typing import Optional, Protocol

from finance_report.reporting_core.application.insider_filling.dtos import InsiderTransaction
from finance_report.reporting_core.domain.shared_values import Provenance, Ticker


class InsiderProvider(Protocol):
    def fetch_transactions(
        self, ticker: Ticker, start_date: date, end_date: date
    ) -> tuple[list[InsiderTransaction], Provenance | None]: ...
