from datetime import date as Date
from decimal import Decimal
from enum import Enum
from typing import Tuple, List, Optional

from .shared_values import ValueObject, ReportId, ReportPayload, Provenance


class WindowUnit(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class Window(ValueObject):
    amount: int = 1
    unit: WindowUnit = WindowUnit.DAY

    @staticmethod
    def one_day() -> "Window":
        return Window(amount=1, unit=WindowUnit.DAY)

    @staticmethod
    def one_week() -> "Window":
        return Window(amount=1, unit=WindowUnit.WEEK)

    @staticmethod
    def one_month() -> "Window":
        return Window(amount=1, unit=WindowUnit.MONTH)

    @staticmethod
    def three_month() -> "Window":
        return Window(amount=3, unit=WindowUnit.MONTH)

    @staticmethod
    def one_year() -> "Window":
        return Window(amount=1, unit=WindowUnit.YEAR)

    @staticmethod
    def two_year() -> "Window":
        return Window(amount=2, unit=WindowUnit.YEAR)

    @property
    def label(self) -> str:
        return f"{self.amount}-{self.unit.value.capitalize()}"


class HighLowEntry(ValueObject):
    window: Window = Window(amount=1, unit=WindowUnit.YEAR)
    high: Decimal
    low: Decimal


class DailyPriceBar(ValueObject):
    """A single raw OHLCV bar as fetched from the data source — reproduction evidence."""
    date: Date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class PriceReport(ReportPayload):
    latest_close: Decimal | None = None
    high_low_entries: tuple[HighLowEntry, ...] = ()
    price_bars: Tuple[DailyPriceBar, ...] = ()

    def to_prompt_context(self) -> str:
        def fmt(x) -> str:
            return f"{Decimal(x):.2f}"

        lines: list[str] = [f"Latest close: {fmt(self.latest_close)}", ""]

        if self.high_low_entries:
            lines.append("Price ranges by window:")
            for e in self.high_low_entries:
                w = f"{e.window.amount}{e.window.unit[0].upper()}"  # 1D, 1W, 1M, 3M, 1Y
                lines.append(f"{w}: high={fmt(e.high)}, low={fmt(e.low)}")
            lines.append("")

        if self.price_bars:
            bars = sorted(self.price_bars, key=lambda b: b.date)
            first, last = bars[0], bars[-1]

            hi_bar = max(bars, key=lambda b: b.high)
            lo_bar = min(bars, key=lambda b: b.low)
            change = (Decimal(last.close) / Decimal(first.close) - 1) * 100

            lines += [
                f"History window: {len(bars)} bars from {first.date} to {last.date}",
                f"  Period open ({first.date} close): {fmt(first.close)}",
                f"  Period close ({last.date} close): {fmt(last.close)}",
                f"  Period change: {change:+.1f}%",
                f"  Period high: {fmt(hi_bar.high)} ({hi_bar.date})",
                f"  Period low:  {fmt(lo_bar.low)} ({lo_bar.date})",
                "",
            ]

            avg_vol = sum(b.volume for b in bars) / len(bars)
            top_vol = sorted(bars, key=lambda b: b.volume, reverse=True)[:4]
            lines.append("Volume:")
            lines.append(f"  Average daily volume: ~{avg_vol / 1_000_000:.1f}M")
            lines.append("  Highest-volume days:")
            for b in top_vol:
                lines.append(f"    {b.date}: {b.volume / 1_000_000:.1f}M (close {fmt(b.close)})")
            lines.append("")

            lines.append("Most recent 5 sessions:")
            for b in bars[-5:]:
                lines.append(f"  {b.date}: close {fmt(b.close)}")

        return "\n".join(lines)

    def summary_focus(self) -> str:
        return (
            "price trend phases over the period, the 52-week high/low range, "
            "notable volume behavior, and the current status relative to that range"
        )

    @classmethod
    def create(cls, report_id: ReportId, price_bars: Tuple[DailyPriceBar, ...], latest_close, windows: List[Window],
               provenance: Optional[Provenance] = None):
        # 1. Implementation of high_low_entries creation
        high_low_entries = []

        # Sort bars by date to ensure tail() logic works correctly if needed,
        # or just assume they are sorted if coming from a provider.
        sorted_bars = sorted(price_bars, key=lambda b: b.date)

        for window in windows:
            # Calculate days needed (rough approximation or exact logic)
            days = cls.window_to_days(window)
            subset = sorted_bars[-days:] if days <= len(sorted_bars) else sorted_bars

            if subset:
                high = max(bar.high for bar in subset)
                low = min(bar.low for bar in subset)
                high_low_entries.append(HighLowEntry(window=window, high=high, low=low))

        return cls(
            report_id=report_id,
            latest_close=latest_close,
            price_bars=price_bars,
            high_low_entries=tuple(high_low_entries),
            provenance=provenance
        )

    @staticmethod
    def window_to_days(window: Window) -> int:
        mapping = {
            WindowUnit.DAY: 1,
            WindowUnit.WEEK: 7,
            WindowUnit.MONTH: 30,
            WindowUnit.YEAR: 365,
        }
        return window.amount * mapping[window.unit]
