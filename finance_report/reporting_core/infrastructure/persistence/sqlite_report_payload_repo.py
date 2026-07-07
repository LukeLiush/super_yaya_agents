import json
import logging
import sqlite3
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, Literal, TypeVar, cast

from finance_report.reporting_core.application.ports.report_repository import ReportPayloadRepository
from finance_report.reporting_core.domain.insider_report import InsiderReport
from finance_report.reporting_core.domain.news_report import NewsReport
from finance_report.reporting_core.domain.price_report import PriceReport
from finance_report.reporting_core.domain.shared_values import ReportPayload

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=ReportPayload)

SCHEMA_UPGRADERS: dict[str, dict[int, Callable[[dict[str, Any]], dict[str, Any]]]] = {
    "price": {},
    "news": {},
    "insider": {},
}

ReportTypeStr = Literal["PriceReport", "NewsReport", "InsiderReport"]


class SqliteReportPayloadRepository(ReportPayloadRepository):
    TYPE_MAP: ClassVar[dict[str, type[ReportPayload]]] = {
        PriceReport.report_type(): PriceReport,
        NewsReport.report_type(): NewsReport,
        InsiderReport.report_type(): InsiderReport,
    }

    def __init__(self, connection: sqlite3.Connection):
        self._connection: sqlite3.Connection = connection
        self._init_db()

    def _init_db(self):
        self._connection.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                report_id TEXT PRIMARY KEY,
                report_type TEXT,
                generated_at TEXT,
                provenance JSON,
                payload JSON
            )
        """)
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_reports_lookup ON reports (report_type, generated_at DESC)"
        )

    def save(self, payload: ReportPayload) -> None:
        # Use mode="json" to get serialized values (datetimes to strings, etc.)
        full: dict = payload.model_dump(mode="json")

        # Base fields become columns; everything else is the blob.
        base_fields: set = set(ReportPayload.model_fields.keys())
        blob = {k: v for k, v in full.items() if k not in base_fields}

        # Handle report_type whether it's a method or a property
        report_type = payload.report_type() if callable(payload.report_type) else payload.report_type

        self._connection.execute(
            """
            INSERT OR REPLACE INTO reports (report_id, report_type, generated_at, provenance, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(payload.report_id.value),
                report_type,
                full["generated_at"],
                json.dumps(full.get("provenance")),
                json.dumps(blob),
            ),
        )

    def get_by_id(self, report_id: str, report_type: type[T] | None = None) -> T:
        row = self._connection.execute(
            "SELECT report_type, report_id, generated_at, provenance, payload FROM reports WHERE report_id = ?",
            (report_id,),
        ).fetchone()

        if not row:
            raise ValueError(f"Report not found: {report_id}")

        return self._row_to_payload(row, report_type)

    def _row_to_payload(self, row: sqlite3.Row, expected_cls: type[T] | None = None) -> T:
        report_type = str(row["report_type"])
        cls = expected_cls or self.TYPE_MAP.get(report_type)

        if not cls:
            raise ValueError(f"Unknown report type: {report_type}")

        # Recombine promoted columns + blob back into one dict for validation.
        data = {
            "report_id": {"value": str(row["report_id"])},
            "generated_at": row["generated_at"],
            "provenance": json.loads(row["provenance"]) if row["provenance"] else None,
            **(json.loads(row["payload"]) if row["payload"] else {}),
        }
        return cast(T, cls.model_validate(data))
