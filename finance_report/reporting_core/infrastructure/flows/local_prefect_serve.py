# serve_flow.py
import logging
import os

from finance_report.reporting_core.infrastructure.config.settings import settings
from finance_report.reporting_core.infrastructure.flows.prefect_finance_report_service import (
    finance_report_flow,
)

os.environ["PREFECT_LOGGING_EXTRA_LOGGERS"] = "finance_report"

# 2. make sure the level is low enough to emit INFO
os.environ["PREFECT_LOGGING_LEVEL"] = "INFO"
logging.getLogger("finance_report").setLevel(logging.INFO)

if __name__ == "__main__":
    finance_report_flow.serve(
        name=settings.prefect_deployment_name,
    )
