from __future__ import annotations

import os
from dataclasses import dataclass

import boto3
from agno.models.aws import AwsBedrock

from invesetment_agent.application.port.ai_agent_service import SingleAgentService
from invesetment_agent.application.usecases.single_stock_summarization_usecase import StockSummarizationUseCase
from invesetment_agent.infrastructure.adapter.agno_agent import AgnoAgentService
from invesetment_agent.infrastructure.utils import set_kb_bedrock_aws_credentials_env_variables


def create_application() -> Application:
    return Application()




@dataclass
class Application:
    def __post_init__(self):
        set_kb_bedrock_aws_credentials_env_variables()
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_session_token = os.getenv("AWS_SESSION_TOKEN")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        session_kwargs = {
            "aws_access_key_id": aws_access_key,
            "aws_secret_access_key": aws_secret_key,
            "aws_session_token": aws_session_token,
            "region_name": aws_region,
        }
        boto_session = boto3.Session(**session_kwargs)
        model = AwsBedrock(
            id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
            # id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            aws_region=aws_region,
            session=boto_session,
            temperature=0.7,
        )

        financial_agent_service: SingleAgentService = AgnoAgentService(model=model,
                                                                       role="Investment Analyst",
                                                                       description="Researches stock prices, analyst recommendations, and  stock fundamentals.")
        self.stock_summarization_use_case: StockSummarizationUseCase = StockSummarizationUseCase(
            financial_agent_service)
