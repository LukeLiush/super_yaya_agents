import logging
from typing import List, Optional

from finance_report.reporting_core.application.market_data.provider import MarketDataProvider
from finance_report.reporting_core.application.ports.report_repository import ReportRequestRepository, ReportPayloadRepository
from finance_report.reporting_core.application.ports.unit_of_work import UnitOfWork
from finance_report.reporting_core.application.use_cases.create_report_request import UseCase
from finance_report.reporting_core.domain.events import ReportRequested
from finance_report.reporting_core.domain.price_report import PriceReport, Window
from finance_report.reporting_core.domain.report_request import ReportRequest
from finance_report.reporting_core.domain.shared_values import FailureContext

logger = logging.getLogger(__name__)


class GeneratePriceReportUseCase(UseCase[ReportRequested, Optional[PriceReport]]):
    def __init__(self,
                 market_data_provider: MarketDataProvider,
                 uow: UnitOfWork,
                 windows: List[Window]) -> None:
        self._market_data_provider: MarketDataProvider = market_data_provider
        self._uow: UnitOfWork = uow
        self._windows = windows

    async def run(self, report_requested: ReportRequested) -> Optional[PriceReport]:
        with self._uow as _uow:
            report_request_repository: ReportRequestRepository = _uow.repository(ReportRequestRepository)
            report_payload_repository: ReportPayloadRepository = _uow.repository(ReportPayloadRepository)

            report_request: Optional[ReportRequest] = \
                report_request_repository.get_by_id(report_requested.report_id)

            if report_request is None:
                raise ValueError("Report request {} not found".format(report_requested.report_id))
            try:

                report_request.mark_as_in_progress()
                price_bars, provenance = self._market_data_provider.fetch_prices(report_request.ticker)
                if price_bars:
                    price_report: PriceReport = PriceReport.create(report_id=report_request.id,
                                                                   price_bars=price_bars,
                                                                   latest_close=price_bars[-1].close,
                                                                   windows=self._windows,
                                                                   provenance=provenance)

                    report_payload_repository.save(price_report)
                    report_request.mark_as_complete()
                    return price_report
                else:
                    report_request.mark_as_failed(FailureContext.from_exception(ValueError(
                        f"No price bars returned for ticker '{report_request.ticker}' "
                        f"(report_id={report_request.id}, as_of={report_request.as_of}, "
                        f"provider returned {len(price_bars)} bars)"
                    )))
            except Exception as exc:
                failure_context = FailureContext.from_exception(exc)
                report_request.mark_as_failed(failure_context)
                logger.exception("Failed to generate price report for %s", report_request.ticker)

            return None
