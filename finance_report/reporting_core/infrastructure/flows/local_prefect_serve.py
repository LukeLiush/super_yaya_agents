# serve_flow.py
import asyncio
import os

from finance_report.reporting_core.infrastructure.config.settings import get_settings, Settings

os.environ["PREFECT_LOGGING_EXTRA_LOGGERS"] = "finance_report"

# 2. make sure the level is low enough to emit INFO
os.environ["PREFECT_LOGGING_LEVEL"] = "INFO"

import logging

logging.basicConfig(  # <-- THIS creates a handler + sets root level
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logging.getLogger("finance_report").setLevel(logging.INFO)

logger = logging.getLogger("finance_report")
logger.setLevel(logging.INFO)

from finance_report.reporting_core.infrastructure.config.secrets import PrefectSecretAdapter
from finance_report.reporting_core.infrastructure.flows.prefect_finance_report_service import (
    finance_report_flow,
)


async def save_secrets():
    from dotenv import load_dotenv

    load_dotenv()
    settings: Settings = await get_settings(use_secret_provider=False)
    for field_name, field_info in settings.model_fields.items():
        extra = field_info.json_schema_extra or {}

        if not extra.get("secret"):
            continue

        secret_name = field_info.alias or field_name
        secret_value = getattr(settings, field_name)

        await PrefectSecretAdapter().save(
            key=secret_name,
            value=secret_value,
        )

        logger.info("Saved Prefect secret '%s'", secret_name)


async def load_secrets():
    # Access the stored secret
    from prefect.settings import (
        PREFECT_API_TLS_INSECURE_SKIP_VERIFY,
        PREFECT_API_URL,
        temporary_settings,
    )
    with temporary_settings(
            {
                PREFECT_API_URL: "https://prefect-l2zy.srv1518966.hstgr.cloud/api",
                PREFECT_API_TLS_INSECURE_SKIP_VERIFY: True,
            }
    ):
        settings = await get_settings()
        print(settings.slack_bot_token)


def main():
    settings = asyncio.run(get_settings())
    finance_report_flow.serve(
        name=settings.prefect_deployment_name,
    )


if __name__ == "__main__":
    asyncio.run(save_secrets())
    main()

    # asyncio.run(load_secrets())
