from datetime import date
from typing import Protocol, List, Tuple, Optional

from finance_report.reporting_core.application.insider_filling.dtos import InsiderTransaction
from finance_report.reporting_core.domain.shared_values import Ticker, Provenance


class InsiderProvider(Protocol):
    def fetch_transactions(self, ticker: Ticker, start_date: date, end_date: date) -> Tuple[
        List[InsiderTransaction], Optional[Provenance]]:
        ...
