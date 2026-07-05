import datetime as dt
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Tuple, Optional

import edgar
import pandas as pd
from edgar import Company
from edgar.entity import EntityFilings
from edgar.ownership import Form4
from tenacity import Retrying, stop_after_attempt, wait_exponential, before_sleep_log

from ...application.insider_filling.dtos import InsiderTransaction
from ...application.insider_filling.provider import InsiderProvider
from ...domain.shared_values import Ticker, Provenance

logger = logging.getLogger(__name__)


class NoFilingsFoundError(Exception):
    """No Form 4 filings exist for this ticker/date range. Permanent — do not retry."""


class TransientDataError(Exception):
    """Network/parse hiccup fetching filings. Safe to retry."""


class EdgarInsiderAdapter(InsiderProvider):
    def __init__(self, retrying: Optional[Retrying] = None, ):
        self.retrying = retrying or Retrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
            before_sleep=before_sleep_log(logger, logging.INFO), )

    def _get_form4_dataframe(self, company: Company, start: str, end: str) -> pd.DataFrame:
        try:
            filings: EntityFilings = company.get_filings(form="4", filing_date=(start, end))
        except (ConnectionError, TimeoutError, OSError) as e:
            # network-level failure → worth retrying
            raise TransientDataError(f"Failed to fetch Form 4 filings: {e}") from e

        if not filings:
            raise NoFilingsFoundError(
                f"No Form 4 filings for {company.tickers} between {start} and {end}"
            )
        logger.info("Discovered %d raw filings. Parsing dataframes...", len(filings))

        dataframes = []
        for filing in filings:
            f4: Form4 = filing.obj()
            df = f4.to_dataframe()
            dataframes.append(df)
        combined_df = pd.concat(dataframes, ignore_index=True)
        sanitized_df = combined_df.replace({pd.NA: None, float('nan'): None})
        if sanitized_df.empty:
            raise NoFilingsFoundError(
                f"Form 4 filings found but contained no transactions for "
                f"{company.tickers} between {start} and {end}"
            )
        return sanitized_df

    def fetch_transactions(self, ticker: Ticker,
                           start_date: dt.date,
                           end_date: dt.date) -> Tuple[List[InsiderTransaction], Optional[Provenance]]:
        company = Company(ticker.symbol)

        start = start_date.strftime("%Y-%m-%d")
        end = end_date.strftime("%Y-%m-%d")

        df: pd.DataFrame = self.retrying(self._get_form4_dataframe, company, start, end)

        provenance: Provenance = Provenance(source=edgar.__name__,
                                            query=f'Company("{ticker.symbol}").get_filings(form="4", filing_date=("{start}", "{end}"))',
                                            queried_at=datetime.now(dt.timezone.utc),
                                            source_version=edgar.__version__)
        return _dataframe_to_transactions(df), provenance


def _dataframe_to_transactions(df: pd.DataFrame) -> List[InsiderTransaction]:
    transactions: List[InsiderTransaction] = []
    for record in df.to_dict(orient="records"):
        try:
            txn = _row_to_transaction(record)
            if txn is not None:
                transactions.append(txn)
        except Exception:
            logger.exception("Failed to convert insider row; row=%s", record)
    return transactions


def _row_to_transaction(row) -> InsiderTransaction | None:
    transaction_date = _to_date(row.get(_COLS["transaction_date"]))
    shares = _to_int(row.get(_COLS["shares"]))
    price = _to_decimal(row.get(_COLS["price"]))
    insider_name = row.get(_COLS["insider_name"])
    code = row.get(_COLS["code"])
    transaction_type = row.get(_COLS["transaction_type"])
    title = row.get(_COLS["insider_title"])

    # Required fields — skip rows missing essentials
    if not (insider_name and transaction_date and code and transaction_type):
        return None
    if shares is None or price is None:
        return None

    return InsiderTransaction(
        insider_name=str(insider_name),
        insider_title=str(title),
        transaction_date=transaction_date,
        code=str(code),
        shares=shares,
        price=price,
        transaction_type=str(transaction_type),
    )


_COLS = {
    "insider_name": "Insider",
    "insider_title": "Position",
    "transaction_date": "Date",
    "code": "Code",
    "shares": "Shares",
    "price": "Price",
    "transaction_type": "Transaction Type",
}


def _to_date(v) -> dt.date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, pd.Timestamp):
        return v.date()
    try:
        return datetime.strptime(str(v), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _to_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(float(v))  # handles "1000.0" and 1000.0
    except (ValueError, TypeError):
        return None


def _to_decimal(v) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))  # str() avoids float binary noise
    except (InvalidOperation, ValueError, TypeError):
        return None
