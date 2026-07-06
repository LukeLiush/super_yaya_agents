# config/settings.py
from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Orchestrator(str, Enum):
    INNGEST = "inngest"
    PREFECT = "prefect"


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
    # inngest_api_key: str = Field(alias="INNGEST_API_KEY")
    inngest_base_url: str = Field(alias="INNGEST_BASE_URL", default="https://api.inngest.com/v1")
    dashscope_api_key: str = Field(alias="DASHSCOPE_API_KEY")
    dashscope_base_url: str = Field(alias="QWEN_BASE_URL", default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    is_production: bool = Field(
        alias="INNGEST_IS_PRODUCTION", default=False, description="Whether the app is running in production mode"
    )
    slack_bot_token: str = Field(alias="SLACK_BOT_TOKEN")  # required, no default
    slack_channel_id: str = Field(alias="SLACK_CHANNEL_ID", default="#super-yaya")

    @property
    def inngest_enabled(self) -> bool:
        return self.orchestrator is Orchestrator.INNGEST


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = Settings()
