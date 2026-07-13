from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.types import TypeDecorator

from finance_report.reporting_core.domain.shared_values import (
    FailureContext, ReportId, ReportStatus, SplitEvent, Ticker,
)


class ReportIdType(TypeDecorator):
    impl = sa.String
    cache_ok = True

    def process_bind_param(self, value: ReportId | None, dialect):
        return value.value if value is not None else None

    def process_result_value(self, value, dialect):
        return ReportId(value=value) if value is not None else None


class TickerType(TypeDecorator):
    impl = sa.String
    cache_ok = True

    def process_bind_param(self, value: Ticker | None, dialect):
        return value.symbol if value is not None else None

    def process_result_value(self, value, dialect):
        return Ticker(symbol=value) if value is not None else None


class ReportStatusType(TypeDecorator):
    impl = sa.String
    cache_ok = True

    def process_bind_param(self, value: ReportStatus | None, dialect):
        return value.value if value is not None else None

    def process_result_value(self, value, dialect):
        return ReportStatus(value) if value is not None else None


class SplitEventType(TypeDecorator):
    impl = sa.JSON
    cache_ok = True

    def process_bind_param(self, value: SplitEvent | None, dialect):
        return value.model_dump(mode="json") if value is not None else None

    def process_result_value(self, value, dialect):
        return SplitEvent.model_validate(value) if value is not None else None


class FailureContextType(TypeDecorator):
    impl = sa.JSON
    cache_ok = True

    def process_bind_param(self, value: FailureContext | None, dialect):
        return value.model_dump(mode="json") if value is not None else None

    def process_result_value(self, value, dialect):
        return FailureContext.model_validate(value) if value is not None else None
