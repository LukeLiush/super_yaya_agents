import asyncio
import os

from prefect.docker import DockerImage

from finance_report.reporting_core.infrastructure.config.settings import get_settings, Settings
from finance_report.reporting_core.infrastructure.flows.local_prefect_serve import save_secrets

os.environ["DOCKER_DEFAULT_PLATFORM"] = "linux/amd64"  # image for linux/amd64
from prefect.settings import (
    PREFECT_API_TLS_INSECURE_SKIP_VERIFY,
    PREFECT_API_URL,
    temporary_settings,
)

from finance_report.reporting_core.infrastructure.flows.prefect_finance_report_service import (
    finance_report_flow,
)

settings: Settings = asyncio.run(get_settings(use_secret_provider=False))

with temporary_settings(
    {
        PREFECT_API_URL: "https://prefect-l2zy.srv1518966.hstgr.cloud/api",
        PREFECT_API_TLS_INSECURE_SKIP_VERIFY: True,
    }
):
    asyncio.run(save_secrets())
    finance_report_flow.deploy(
        name=settings.prefect_deployment_name,
        work_pool_name="my-docker-pool",
        image=DockerImage(
            name="ethankulakula/super-yaya-slack-bot",
            tag="latest",
            dockerfile="finance_report/reporting_core/infrastructure/flows/Dockerfile",
            build_backend="buildx",  # <-- enables multi-platform
            platforms=["linux/amd64"],  # <-- forwarded to buildx.build()
        ),
        build=True,
        push=True,
        job_variables={
            "networks": ["prefect-l2zy_default"],
            "env": {
                "PREFECT_LOGGING_EXTRA_LOGGERS": "finance_report",
                "PREFECT_LOGGING_LEVEL": "INFO",
            },
        },
    )
