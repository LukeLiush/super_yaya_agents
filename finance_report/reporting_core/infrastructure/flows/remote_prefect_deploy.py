from prefect import flow
from prefect.settings import temporary_settings, PREFECT_API_URL, PREFECT_API_TLS_INSECURE_SKIP_VERIFY

from finance_report.reporting_core.infrastructure.config.settings import settings

REPO_URL = "https://github.com/LukeLiush/super_yaya_agents.git"  # <-- your repo
ENTRYPOINT = (
    "finance_report/reporting_core/infrastructure/flows/"
    "prefect_finance_report_service.py:finance_report_flow"
)

with temporary_settings({
    PREFECT_API_URL: "https://prefect-l2zy.srv1518966.hstgr.cloud/api",
    PREFECT_API_TLS_INSECURE_SKIP_VERIFY: True,
}):
    flow.from_source(
        source=REPO_URL,
        entrypoint=ENTRYPOINT,
    ).deploy(
        name=settings.prefect_deployment_name,
        work_pool_name="default-pool",  # process pool
        # image="ethankulakula/super-yaya-slack-bot:latest",
        # build=True,
        # push=True,
        # schedules=[CronSchedule(cron="30 6 * * 1-5", timezone="America/Los_Angeles")],
        # parameters={
        #     "report_trigger_request": {"ticker": "TSLA", "report_types": ["price", "insider", "news"]},
        #     "requested_by": "scheduler",
        # },
    )
