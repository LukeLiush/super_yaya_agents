from datetime import date
from decimal import Decimal

from finance_report.reporting_core.application.insider_filling.dtos import InsiderTransaction
from finance_report.reporting_core.domain.shared_values import ReportId, ReportPayload, Ticker


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
        lines: list[str] = [
            "INSIDER TRANSACTION DATA (authoritative source of truth)",
            "Use ONLY these facts. Do not invent names, titles, dates, codes, shares, or prices.",
        ]

        if self.period_start and self.period_end:
            lines.append(f"Period: {self.period_start.isoformat()} to {self.period_end.isoformat()}")
        else:
            lines.append("Period: not provided")

        lines.extend(
            [
                f"Transaction count: {self.transaction_count}",
                (
                    f"Net insider shares traded: {self.net_shares_traded} "
                    "(positive = net buying, negative = net selling)"
                ),
                "",
                "Transactions:",
            ]
        )

        if not self.transactions:
            lines.append("- None provided.")
            return "\n".join(lines)

        shown = self.transactions[:500]
        for i, tx in enumerate(shown, start=1):
            lines.append(self._format_transaction(i, tx))

        omitted = self.transaction_count - len(shown)
        if omitted > 0:
            lines.append(f"- ... {omitted} additional transaction(s) omitted from context.")

        return "\n".join(lines)

    def _format_transaction(self, idx: int, tx: InsiderTransaction) -> str:
        return (
            f"- [{idx}] "
            f"insider_name={tx.insider_name!s} | "
            f"insider_title={tx.insider_title!s} | "
            f"transaction_date={tx.transaction_date.isoformat()} | "
            f"code={tx.code} | "
            f"transaction_type={tx.transaction_type} | "
            f"shares={tx.shares} | "
            f"price={self._format_decimal(tx.price)}"
        )

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        # Avoid scientific notation / noisy trailing zeros in prompts
        return format(value, "f")

    def summary_focus(self) -> str:
        return (
            "the direction and scale of insider activity (buying vs selling) "
            "and whether it signals confidence or caution"
        )

    @classmethod
    def create(cls, report_id: ReportId, transactions, period_start, period_end, provenance):
        return cls(
            report_id=report_id,
            transactions=tuple(transactions),
            period_start=period_start,
            period_end=period_end,
            provenance=provenance,
        )
