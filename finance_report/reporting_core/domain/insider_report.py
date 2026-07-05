from datetime import date

from .shared_values import Ticker, ReportPayload, ReportId
from ..application.insider_filling.dtos import InsiderTransaction


class InsiderReport(ReportPayload):
    transactions: tuple[InsiderTransaction, ...] = ()
    period_start: date | None = None
    period_end: date | None = None

    @property
    def transaction_count(self) -> int:
        return len(self.transactions)

    @property
    def net_shares_traded(self) -> int:
        # positive = net buying, negative = net selling
        return sum(t.shares for t in self.transactions)

    def to_prompt_context(self) -> str:
        lines = []
        if self.period_start and self.period_end:
            lines.append(f"Period: {self.period_start} to {self.period_end}")
        lines.append(f"Transaction count: {self.transaction_count}")
        lines.append(f"Net insider shares traded: {self.net_shares_traded}")
        return "\n".join(lines)

    def summary_focus(self) -> str:
        return (
            "the direction and scale of insider activity (buying vs selling) "
            "and whether it signals confidence or caution"
        )

    @classmethod
    def create(cls, report_id: ReportId, ticker: Ticker, transactions, period_start, period_end, provenance):
        return cls(report_id=report_id, transactions=tuple(transactions),
                   period_start=period_start, period_end=period_end, provenance=provenance)
