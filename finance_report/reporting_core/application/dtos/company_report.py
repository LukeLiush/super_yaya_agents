from typing import Optional

from pydantic import BaseModel

from finance_report.reporting_core.domain.insider_report import InsiderReport
from finance_report.reporting_core.domain.news_report import NewsReport
from finance_report.reporting_core.domain.price_report import PriceReport


class CompanyFinanceReport(BaseModel):
    ticker: str
    price_report: PriceReport | None = None
    news_report: NewsReport | None = None
    insider_report: InsiderReport | None = None

    @property
    def is_complete(self) -> bool:
        return all([self.price_report, self.news_report, self.insider_report])
