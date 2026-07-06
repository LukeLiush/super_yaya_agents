from datetime import datetime

from pydantic import model_validator

from finance_report.reporting_core.application.news.dtos import NewsItem
from finance_report.reporting_core.domain.shared_values import Provenance, ReportId, ReportPayload


class NewsReport(ReportPayload):
    items: list[NewsItem]
    since: datetime | None = None

    @model_validator(mode="after")
    def _order_newest_first(self):
        # invariant: items always newest-first
        object.__setattr__(
            self,
            "items",
            sorted(self.items, key=lambda i: i.published_at, reverse=True),
        )
        return self

    @classmethod
    def create(cls, report_id: ReportId, items: list[NewsItem], provenance: Provenance | None = None) -> "NewsReport":
        return cls(report_id=report_id, items=items, provenance=provenance)

    def to_prompt_context(self) -> str:
        if not self.items:
            span = f" since {self.since:%Y-%m-%d}" if self.since else ""
            return f"No news items available{span}."

        header_parts = [f"News items: {len(self.items)}"]
        if self.since:
            header_parts.append(f"since {self.since:%Y-%m-%d}")
        # items are guaranteed newest-first by the invariant
        header_parts.append(f"covering {self.items[-1].published_at:%Y-%m-%d} to {self.items[0].published_at:%Y-%m-%d}")
        lines = [", ".join(header_parts), ""]

        for item in self.items:
            lines.append(f"[{item.published_at:%Y-%m-%d}] ({item.publisher}) {item.headline}")
            if item.summary:
                lines.append(f"    {item.summary}")

        return "\n".join(lines)

    def summary_focus(self) -> str:
        return (
            "the dominant themes across recent headlines, any material or "
            "market-moving developments, the overall sentiment (positive, "
            "negative, or mixed), and how recent the coverage is"
        )
