from pydantic import BaseModel

from .shared_values import Ticker, ReportId, ValueObject


class ReportRequested(ValueObject):
    report_id: ReportId
    ticker: Ticker
    requested_by: str
