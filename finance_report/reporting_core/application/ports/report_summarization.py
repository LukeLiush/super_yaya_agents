from typing import Protocol

from ...domain.shared_values import ReportPayload


class ReportSummarizer(Protocol):
    async def summarize(self, report: ReportPayload) -> str: ...
