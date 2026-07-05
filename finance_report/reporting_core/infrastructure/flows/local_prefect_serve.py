# serve_flow.py
from finance_report.reporting_core.infrastructure.config.settings import settings
from finance_report.reporting_core.infrastructure.flows.prefect_finance_report_service import (
    finance_report_flow,
)

if __name__ == "__main__":
    finance_report_flow.serve(name=settings.prefect_deployment_name)
