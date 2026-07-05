from typing import Protocol

from finance_report.reporting_core.domain.shared_values import ReportPayload


class ReportSummarizer(Protocol):
    async def summarize(self, report: ReportPayload) -> str: ...
