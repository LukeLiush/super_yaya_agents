from __future__ import annotations

import os
from dataclasses import dataclass

from agno.models.deepseek import DeepSeek
from agno.models.google import Gemini
from agno.models.groq import Groq
from agno.models.huggingface import HuggingFace
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv

from invesetment_agent.application.port.ai_agent_service import AgentService
from invesetment_agent.application.usecases.equity_summarization_usecase import EquitySummarizationUseCase
from invesetment_agent.infrastructure.adapter.agno_agent import FallbackAgnoAgentService, FinancialAgnoAgentService
from invesetment_agent.infrastructure.adapter.agno_financial_agent import AgnoFinancialAgent

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
        return FallbackAgnoAgentService(agent_services=[
            # hf_service,
            google_service,
            # groq,
            # deepseek,
            # openrouter,
        ])

    @staticmethod
    def create_openrouter_agent_service() -> AgentService:
        # https://openrouter.ai/settings/keys
        openrouter_api_key = os.environ.get("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY not set in environment. Please set it (e.g., in .env).")

        model = OpenRouter(
            # id="google/gemini-2.0-flash-exp:free",
            # id="nex-agi/deepseek-v3.1-nex-n1:free",
            id="google/gemini-2.0-flash-exp:free",
            api_key=openrouter_api_key,

        )

        return FinancialAgnoAgentService(model=model, )

    @staticmethod
    def create_deepseek_agent_service() -> AgentService:
        # https://deepseek.com/account/api-keys
        deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set in environment. Please set it (e.g., in .env).")

        model = DeepSeek(
            id="deepseek-chat",
            api_key=deepseek_api_key,
        )

        return FinancialAgnoAgentService(model=model, )

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

        return FinancialAgnoAgentService(model=model)

    @staticmethod
    def create_google_agent_service() -> AgentService:
        # https://aistudio.google.com/api-keys
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if not google_api_key:
            raise RuntimeError("GOOGLE_API_KEY not set in environment. Please set it (e.g., in .env).")

        model = Gemini(
            id="gemini-3-flash-preview",
            api_key=google_api_key,

        )
        return AgnoFinancialAgent.from_single_model(model=model)

    @staticmethod
    def create_hf_agent_service() -> AgentService:
        # https://huggingface.co/settings/tokens
        hf_api_key = os.environ.get("HF_API_KEY")
        if not hf_api_key:
            raise RuntimeError("HF_API_KEY not set in environment. Please set it (e.g., in .env).")

        # Confirm this model id is available and permitted for your token/account
        model = HuggingFace(
            id="deepseek-ai/DeepSeek-V3",
            api_key=hf_api_key,
            base_url="https://router.huggingface.co/v1"
        )

        return FinancialAgnoAgentService(model=model)

    def __post_init__(self):
        agent_service = self.create_fallback_agent_service()
        self.stock_summarization_use_case: EquitySummarizationUseCase = EquitySummarizationUseCase(agent_service)
