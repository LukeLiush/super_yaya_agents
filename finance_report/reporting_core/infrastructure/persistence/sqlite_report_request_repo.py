import json
import sqlite3
from typing import Optional

from finance_report.reporting_core.application.ports.report_repository import ReportRequestRepository
from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.domain.shared_values import ReportId, Ticker


class SqliteReportRequestRepository(ReportRequestRepository):
    def __init__(self, connection: sqlite3.Connection):
        self._connection: sqlite3.Connection = connection
        self._init_db()

    def _init_db(self):
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS report_requests (
                id TEXT PRIMARY KEY,
                ticker TEXT,
                requested_by TEXT,
                status TEXT,
                data JSON,
                requested_at TEXT
            )
        """)

    def save(self, request: ReportRequest) -> None:
        data = request.model_dump(exclude={"id", "ticker", "requested_by", "status", "requested_at"})
        self._connection.execute(
            """
            INSERT OR REPLACE INTO report_requests (id, ticker, requested_by, status, data, requested_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                request.id.value,
                request.ticker.symbol,
                request.requested_by,
                request.status.value,
                json.dumps(data, default=str),
                request.requested_at.isoformat(),
            ),
        )

    def get_by_id(self, report_id: ReportId) -> ReportRequest | None:
        row = self._connection.execute("SELECT * FROM report_requests WHERE id = ?", (report_id.value,)).fetchone()

        if not row:
            return None

        data = json.loads(row["data"])
        return ReportRequest(
            id=ReportId(value=row["id"]),
            ticker=Ticker(symbol=row["ticker"]),
            requested_by=row["requested_by"],
            status=row["status"],
            requested_at=row["requested_at"],
            **data,
        )
