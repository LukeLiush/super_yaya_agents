from dataclasses import dataclass, field
from typing import List

import yfinance


@dataclass(frozen=True)
class SingleStockSummarizationRequest:
    stock: str
    instructions: List[str] = field(default_factory=lambda: [
        "provide: 5-year, 1-year and 30-day high/low points in a table, \n"
        "provide: 2-month trend prediction, \n"
        "provide: buying time recommendation for current month vs next month, \n"
        "provide: daily monitoring suggestions.\n", ])

    def is_valid(self)-> bool:
        try:
            ticker = yfinance.Ticker(self.stock)
            info = ticker.info
            return 'symbol' in info or 'shortName' in info
        except:
            return False



@dataclass(frozen=True)
class MultiStockSummarizationRequest:
    single_requests: List[SingleStockSummarizationRequest] = field(default_factory=lambda: [])
