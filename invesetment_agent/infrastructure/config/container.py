from __future__ import annotations

import os
from dataclasses import dataclass

from agno.models.google import Gemini
from agno.models.groq import Groq
from dotenv import load_dotenv

from invesetment_agent.application.port.ai_agent_service import AgentService
from invesetment_agent.application.usecases.ticker_summarization_usecase import EquitySummarizationUseCase
from invesetment_agent.infrastructure.adapter.agno_agent import FallbackAgnoAgentService
from invesetment_agent.infrastructure.adapter.agno_financial_team import (
    AgnoFinancialAgent,
    AgnoFinancialTeam,
    AgnoNewsSentimentAgent,
    AgnoStylerAgent,
)

load_dotenv(verbose=True)


def create_application() -> Application:
    return Application()


@dataclass
class Application:
    def create_fallback_agent_service(self) -> AgentService:
        # hf_service = self.create_hf_agent_service()
        google_service = self.create_google_agent_service()
        # groq = self.create_grok_agent_service()
        # deepseek = self.create_deepseek_agent_service()
        # openrouter = self.create_openrouter_agent_service()
        return FallbackAgnoAgentService(
            agent_services=[
                # hf_service,
                google_service,
                # groq,
                # deepseek,
                # openrouter,
            ]
        )

    @staticmethod
    def create_grok_agent_service() -> AgentService:
        # https://console.groq.com/keys
        grok_api_key = os.environ.get("GROK_API_KEY")
        if not grok_api_key:
            raise RuntimeError("GROK_API_KEY not set in environment. Please set it (e.g., in .env).")

        model = Groq(
            id="llama-3.3-70b-versatile",
            api_key=grok_api_key,
        )
        return AgnoFinancialTeam(
            model=model,
            agno_agent_services=[
                AgnoFinancialAgent(model=model),
                AgnoStylerAgent(model=model),
                AgnoNewsSentimentAgent(model=model),
            ],
        )

    @staticmethod
    def create_google_agent_service() -> AgentService:
        # https://aistudio.google.com/api-keys
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            raise RuntimeError("GOOGLE_API_KEY not set in environment. Please set it (e.g., in .env).")

        # RECOMMENDATIONS for Model Selection:
        # 1. Team Leader: Needs high reasoning for orchestration. Use Gemini Pro.
        # 2. Finance Agent: Data heavy, but structured. Gemini Flash is sufficient.
        # 3. News Sentiment Agent: Search and summarize. Gemini Flash is sufficient.
        # 4. Styler Agent: Formatting and analogies. Gemini Flash is sufficient.

        # For this implementation, we'll use:
        # - gemini-pro-latest for the Team Leader (Orchestrator) - High reasoning
        # - gemini-2.0-flash for all sub-agents - High speed, low cost, excellent performance

        leader_model = Gemini(
            # id="gemini-pro-latest",
            id="gemini-3-flash-preview",
            api_key=google_api_key,
        )

        sub_agent_model = Gemini(
            # id="gemini-2.0-flash",0-flash
            id="gemini-3-flash-preview",
            api_key=google_api_key,
        )

        team: AgentService = AgnoFinancialTeam(
            model=leader_model,
            agno_agent_services=[
                AgnoFinancialAgent(model=sub_agent_model),
                AgnoStylerAgent(model=sub_agent_model),
                AgnoNewsSentimentAgent(model=sub_agent_model),
            ],
        )
        return team

    def __post_init__(self) -> None:
        agent_service: AgentService = self.create_fallback_agent_service()
        self.stock_summarization_use_case: EquitySummarizationUseCase = EquitySummarizationUseCase(agent_service)
