from typing import Optional
from pydantic import BaseModel
from ...domain.price_report import PriceReport
from ...domain.news_report import NewsReport
from ...domain.insider_report import InsiderReport

class CompanyFinanceReport(BaseModel):
    ticker: str
    price_report: Optional[PriceReport] = None
    news_report: Optional[NewsReport] = None
    insider_report: Optional[InsiderReport] = None

    @property
    def is_complete(self) -> bool:
        return all([self.price_report, self.news_report, self.insider_report])
