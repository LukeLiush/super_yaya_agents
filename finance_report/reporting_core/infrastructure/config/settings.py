# config/settings.py
import asyncio
import logging
from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from finance_report.reporting_core.infrastructure.config.secrets import SecretProvider, PrefectSecretProvider, \
    EnvSecretProvider

logger = logging.getLogger(__name__)


class Orchestrator(str, Enum):
    INNGEST = "inngest"
    PREFECT = "prefect"


def get_secret_provider(orchestrator: Orchestrator) -> SecretProvider:
    if orchestrator is Orchestrator.PREFECT:
        return PrefectSecretProvider()
    return EnvSecretProvider()


def _check_required(env_var: str, value: str, required: bool) -> None:
    """Emit a clear warning when a required secret ends up empty."""
    if required and not value:
        logger.warning(
            "Required secret env_var=%r resolved to an empty value; "
            "downstream use will likely fail. Ensure the Prefect block or "
            "environment variable is set.",
            env_var,
        )


def SecretField(  # noqa: N802 - factory, mimics Field()
        *,
        env_var: str,
        required: bool = True,
        default: str = "",
        description: str | None = None,
):
    return Field(
        default=default,
        alias=env_var,
        description=description,
        json_schema_extra={
            "secret": True,
            "env_var": env_var,
            "required": required,
        },
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    orchestrator: Orchestrator = Orchestrator.PREFECT
    prefect_deployment_name: str = Field(alias="PREFECT_DEPLOYMENT_NAME", default="finance-report")
    prefect_server_url: str = Field(alias="PREFECT_SERVER_URL", default="http://localhost:4200")
    prefect_api_url: str = Field(alias="PREFECT_API_URL", default="http://localhost:4200/api")
    inngest_base_url: str = Field(alias="INNGEST_BASE_URL", default="https://api.inngest.com/v1")
    dashscope_base_url: str = Field(alias="QWEN_BASE_URL", default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    is_production: bool = Field(
        alias="INNGEST_IS_PRODUCTION", default=False, description="Whether the app is running in production mode"
    )
    slack_channel_id: str = Field(alias="SLACK_CHANNEL_ID", default="#super-yaya")
    prefect_flow_name: str = Field(alias="PREFECT_FLOW_NAME", default="finance-report-flow")

    dashscope_api_key: str = SecretField(
        env_var="DASHSCOPE_API_KEY",
    )
    slack_bot_token: str = SecretField(
        env_var="SLACK_BOT_TOKEN",
    )

    @property
    def inngest_enabled(self) -> bool:
        return self.orchestrator is Orchestrator.INNGEST

    async def resolve_secrets(self) -> None:

        provider = get_secret_provider(self.orchestrator)
        logger.info("Hydrating secrets via %s", type(provider).__name__)

        for name, field in type(self).model_fields.items():
            extra = field.json_schema_extra or {}
            if not (isinstance(extra, dict) and extra.get("secret")):
                continue  # not a SecretField -> skip

            env_var: str = extra["env_var"]
            required: bool = extra.get("required", True)

            # 1-2. ask the provider (Prefect block, etc.)
            resolved: str | None = None
            try:
                resolved = await provider.get(env_var)
            except Exception:
                logger.exception(
                    "Provider failed resolving secret field=%r env_var=%r; "
                    "falling back to current field value",
                    name,
                    env_var,
                )

            # 3. fall back to whatever pydantic loaded from env/.env/default
            if not resolved:
                resolved = getattr(self, name) or ""

            # 4. write it back onto the field
            object.__setattr__(self, name, resolved)
            if resolved:
                logger.info("Hydrated secret field=%r (len=%d)", name, len(resolved))
            elif required:
                logger.warning(
                    "Required secret field=%r (env_var=%r) resolved to empty; "
                    "downstream use will likely fail.",
                    name,
                    env_var,
                )
            else:
                logger.info("Optional secret field=%r (env_var=%r) is empty", name, env_var)


_settings: Settings | None = None
_lock = asyncio.Lock()


async def get_settings(use_secret_provider: bool = True) -> Settings:
    global _settings
    if _settings is not None:
        return _settings
    async with _lock:
        if _settings is not None:
            return _settings
        the_settings = Settings()
        if use_secret_provider:
            await the_settings.resolve_secrets()
        _settings = the_settings
        return _settings
