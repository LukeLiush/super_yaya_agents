import typing
from dataclasses import dataclass
from typing import Callable, Awaitable, Any

from lagom import Container

from finance_report.reporting_core.application.insider_filling.generate_report import GenerateInsiderReportUseCase
from finance_report.reporting_core.application.market_data.generate_report import GeneratePriceReportUseCase
from finance_report.reporting_core.application.news.generate_report import GenerateNewsReportUseCase
from finance_report.finance_sdk.schemas import ReportType, UnknownReportType


# report_registry.py
@dataclass(frozen=True)
class ReportHandler:
    run: Callable[..., Awaitable[Any]]

    @property
    def return_type(self) -> Any:
        return typing.get_type_hints(self.run).get("return")


def build_report_registry(container: Container) -> dict[ReportType, ReportHandler]:
    return {
        ReportType.PRICE: ReportHandler(container[GeneratePriceReportUseCase].run),
        ReportType.NEWS: ReportHandler(container[GenerateNewsReportUseCase].run),
        ReportType.INSIDER: ReportHandler(container[GenerateInsiderReportUseCase].run),
    }


class ReportRegistry:
    def __init__(self, container: Container):
        self._handlers = build_report_registry(container)

    def handler_for(self, report_type: ReportType) -> ReportHandler:
        try:
            return self._handlers[report_type]
        except KeyError:
            raise UnknownReportType(report_type)

    def known_types(self) -> tuple[ReportType, ...]:
        return tuple(self._handlers)
