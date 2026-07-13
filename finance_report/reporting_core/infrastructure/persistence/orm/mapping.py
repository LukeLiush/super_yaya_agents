from __future__ import annotations

import logging

from sqlalchemy import Column, Date, DateTime, MetaData, String, Table, JSON, Index
from sqlalchemy.orm import registry

from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.infrastructure.persistence.orm.types import (
    FailureContextType, ReportIdType, ReportStatusType, SplitEventType, TickerType,
)

logger = logging.getLogger(__name__)

metadata = MetaData()
mapper_registry = registry(metadata=metadata)

reports_table = Table(
    "reports",
    metadata,
    Column("report_id", String, primary_key=True),
    Column("report_type", String, nullable=False),
    Column("generated_at", String, nullable=False),
    Column("provenance", JSON, nullable=True),
    Column("payload", JSON, nullable=False),
    Index("idx_reports_lookup", "report_type", "generated_at"),
)

report_requests_table = Table(
    "report_requests",
    metadata,
    Column("id", ReportIdType, primary_key=True),
    Column("ticker", TickerType, nullable=False),
    Column("requested_by", String, nullable=False),
    Column("split_event", SplitEventType, nullable=True),
    Column("as_of", Date, nullable=False),
    Column("status", ReportStatusType, nullable=False),
    Column("failure_context", FailureContextType, nullable=True),
    Column("requested_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("completed_at", DateTime, nullable=True),
)

_mapping_started = False


def start_mappers() -> None:
    """Instrument the domain class for persistence. Idempotent; call once at startup."""
    global _mapping_started
    if _mapping_started:
        logger.debug("Mappers already started; skipping.")
        return
    mapper_registry.map_imperatively(ReportRequest, report_requests_table)
    _mapping_started = True
    logger.info("Imperative mappers started for ReportRequest.")
