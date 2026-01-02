from dataclasses import dataclass, field
from typing import List

import yfinance


@dataclass(frozen=True)
class SingleTickerSummarizationRequest:
    ticker: str

    @property
    def query(self) -> str:
        return f"Analyze the {self.ticker} and provide a detailed investment report."

    @property
    def instructions(self):
        return []

    def is_valid(self) -> bool:
        try:
            ticker = yfinance.Ticker(self.ticker)
            info = ticker.info
            return 'symbol' in info or 'shortName' in info
        except:
            return False


@dataclass(frozen=True)
class MultiTickerSummarizationRequest:
    single_requests: List[SingleTickerSummarizationRequest] = field(default_factory=lambda: [])
