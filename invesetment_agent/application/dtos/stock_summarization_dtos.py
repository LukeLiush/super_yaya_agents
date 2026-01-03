from dataclasses import dataclass, field

import yfinance


@dataclass(frozen=True)
class SingleTickerSummarizationRequest:
    ticker: str

    @property
    def query(self) -> str:
        return f"Analyze the {self.ticker} and provide a detailed investment report."

    def is_valid(self) -> bool:
        try:
            ticker = yfinance.Ticker(self.ticker)
            info = ticker.info
            return "symbol" in info or "shortName" in info
        except Exception:
            return False


@dataclass(frozen=True)
class MultiTickerSummarizationRequest:
    single_requests: list[SingleTickerSummarizationRequest] = field(default_factory=lambda: [])
