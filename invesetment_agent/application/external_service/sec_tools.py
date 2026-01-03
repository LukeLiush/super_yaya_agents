import os
import xml.etree.ElementTree as ET
from typing import Any

import requests  # type: ignore
from agno.tools import tool

# SEC requires a descriptive User-Agent with an email
SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "InvestmentAgent/1.0 (contact@example.com)")


@tool()
def resolve_cik(ticker: str) -> str:
    """
    Resolve a stock ticker to a zero-padded SEC CIK.
    """
    return _resolve_cik(ticker)


@tool()
def fetch_sec_submissions(cik: str) -> dict:
    """
    Fetch SEC submission JSON for a given CIK.
    """
    return _fetch_sec_submissions(cik)


@tool()
def fetch_latest_filing_link(ticker: str, form_type: str = "10-K") -> str:
    """
    Fetch the URL for the most recent filing of a specific type (e.g., '10-K', '10-Q', '8-K').
    """
    return _fetch_latest_filing_link(ticker, form_type)


@tool()
def build_insider_table(ticker: str) -> str:
    """
    Fetch recent insider transactions for a ticker and format them as an ASCII table.
    """
    return _build_insider_table(ticker)


SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "Example App contact@example.com")


def _get_headers() -> dict[str, str]:
    return {
        "User-Agent": SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
    }


def _resolve_cik(ticker: str) -> str:
    """
    Resolve a stock ticker to a zero-padded SEC CIK.
    """
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=_get_headers())
    resp.raise_for_status()
    data = resp.json()

    ticker = ticker.upper()
    for entry in data.values():
        if entry["ticker"] == ticker:
            return str(entry["cik_str"]).zfill(10)

    raise ValueError(f"CIK not found for ticker: {ticker}")


def _fetch_sec_submissions(cik: str) -> dict[Any, Any]:
    """
    Fetch SEC submission JSON for a given CIK.
    """
    # Ensure CIK is 10 digits
    cik = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    resp = requests.get(url, headers=_get_headers())
    resp.raise_for_status()
    return dict(resp.json())


def _fetch_latest_filing_link(ticker: str, form_type: str = "10-K") -> str:
    """
    Fetch the URL for the most recent filing of a specific type (e.g., '10-K', '10-Q', '8-K').
    """
    cik = _resolve_cik(ticker)
    submissions = _fetch_sec_submissions(cik)
    filings = submissions.get("filings", {}).get("recent", {})

    forms = filings.get("form", [])
    acc_nums = filings.get("accessionNumber", [])
    primary_docs = filings.get("primaryDocument", [])

    for f, acc, doc in zip(forms, acc_nums, primary_docs, strict=False):
        if f.upper() == form_type.upper():
            acc_clean = acc.replace("-", "")
            return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc}"

    return f"No recent {form_type} filing found for {ticker}."


def _fetch_form4_transactions(ticker: str, limit: int = 5) -> list[dict]:
    """
    Fetch and parse recent Form 4 insider transactions for a company.
    """
    cik = _resolve_cik(ticker)
    submissions = _fetch_sec_submissions(cik)
    filings = submissions.get("filings", {}).get("recent", {})

    forms = filings.get("form", [])
    accession_numbers = filings.get("accessionNumber", [])
    primary_documents = filings.get("primaryDocument", [])
    filing_dates = filings.get("filingDate", [])

    records = []
    for form, acc, doc, date in zip(forms, accession_numbers, primary_documents, filing_dates, strict=False):
        if form != "4":
            continue

        acc_clean = acc.replace("-", "")
        # The primaryDocument in JSON might have a prefix like xslF345X05/
        # We need the raw XML which is usually just the file name at the end
        xml_name = doc.split("/")[-1]
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_clean}/{xml_name}"

        try:
            resp = requests.get(url, headers=_get_headers())
            resp.raise_for_status()

            # Simple XML parsing for Form 4
            root = ET.fromstring(resp.content)

            # Reporting Owner
            rpt_owner = root.find(".//reportingOwner/reportingOwnerId/rptOwnerName")
            owner_name = rpt_owner.text if rpt_owner is not None else "Unknown"

            # Non-Derivative Transactions
            for tx in root.findall(".//nonDerivativeTransaction"):
                security_title = tx.find(".//securityTitle/value")
                tx_date = tx.find(".//transactionDate/value")
                tx.find(".//transactionCoding/transactionCode")
                tx_amounts = tx.find(".//transactionAmounts")

                if tx_amounts is not None:
                    shares = tx_amounts.find(".//transactionShares/value")
                    price = tx_amounts.find(".//transactionPricePerShare/value")
                    acquired_disposed = tx_amounts.find(".//transactionAcquiredDisposedCode/value")

                    action = "Buy" if acquired_disposed is not None and acquired_disposed.text == "A" else "Sell"

                    records.append(
                        {
                            "date": tx_date.text if tx_date is not None else date,
                            "name": owner_name,
                            "action": action,
                            "price": price.text if price is not None else "0",
                            "shares": shares.text if shares is not None else "0",
                            "security": security_title.text if security_title is not None else "Security",
                        }
                    )

                if len(records) >= limit:
                    break
        except Exception:
            # Skip failures and move to next
            continue

        if len(records) >= limit:
            break

    return records


@tool()
def fetch_form4_transactions(ticker: str, limit: int = 5) -> list[dict]:
    """
    Fetch and parse recent Form 4 insider transactions for a company.
    Returns a list of transaction dictionaries with Date, Insider Name, Action, Price, and Shares.
    """
    return _fetch_form4_transactions(ticker, limit)


def _build_insider_table(ticker: str) -> str:
    """
    Fetch recent insider transactions for a ticker and format them as an ASCII table.
    """
    try:
        transactions = _fetch_form4_transactions(ticker)
        if not transactions:
            return f"No recent insider transactions found for {ticker}."

        lines = []
        lines.append(f"Recent Insider Activity for {ticker.upper()}")
        lines.append("Date       | Insider Name          | Action | Price ($) | Shares")
        lines.append("-----------|-----------------------|--------|-----------|---------")

        for tx in transactions:
            name = (tx.get("name", "Unknown")[:21]).ljust(21)
            lines.append(
                f"{tx.get('date', '----')} | "
                f"{name} | "
                f"{tx.get('action', '-').ljust(6)} | "
                f"{str(tx.get('price', '-')).ljust(9)} | "
                f"{tx.get('shares', '-')}"
            )

        return "```\n" + "\n".join(lines) + "\n```"
    except Exception as e:
        return f"Error building insider table for {ticker}: {e}"


if __name__ == "__main__":
    print(_build_insider_table("AAPL"))
