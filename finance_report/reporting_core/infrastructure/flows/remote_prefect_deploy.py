# serve_flow.py
import asyncio

from prefect import get_client
from prefect.client.schemas.actions import WorkPoolCreate
from prefect.exceptions import ObjectNotFound
from prefect.settings import temporary_settings, PREFECT_API_URL, PREFECT_API_TLS_INSECURE_SKIP_VERIFY, \
    get_current_settings
from prefect_docker import DockerWorker

from finance_report.reporting_core.infrastructure.config.settings import settings
from finance_report.reporting_core.infrastructure.flows.prefect_finance_report_service import (
    finance_report_flow,
)
with temporary_settings({
    PREFECT_API_URL: "https://prefect-l2zy.srv1518966.hstgr.cloud/api",
    PREFECT_API_TLS_INSECURE_SKIP_VERIFY: True,
}):
    finance_report_flow.deploy(
        name=settings.prefect_deployment_name,
        work_pool_name="default-pool", # process pool
        #image="ethankulakula/super-yaya-slack-bot:latest",
        #build=True,
        #push=True,
        # schedules=[CronSchedule(cron="30 6 * * 1-5", timezone="America/Los_Angeles")],
        # parameters={
        #     "report_trigger_request": {"ticker": "TSLA", "report_types": ["price", "insider", "news"]},
        #     "requested_by": "scheduler",
        # },
    )
