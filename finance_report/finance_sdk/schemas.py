from enum import Enum

from pydantic import BaseModel, Field


class UnknownReportType(Exception): ...


class ReportType(str, Enum):
    PRICE = "price"
    INSIDER = "insider"
    NEWS = "news"
    # To add a new report, just add it here!
    # VALUATION = "valuation"


class ReportTriggerRequest(BaseModel):
    ticker: str = Field(..., description="The stock ticker symbol (e.g., AAPL, TSLA)")
    report_types: list[ReportType] = Field(
        default=[ReportType.PRICE, ReportType.INSIDER, ReportType.NEWS], description="List of report types to generate"
    )


class ReportTriggerResponse(BaseModel):
    message: str
    ticker: str
    id: str
