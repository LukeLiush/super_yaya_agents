from typing import Optional, List, Union

from agno.agent import Agent
from agno.models.base import Model
from agno.run import RunStatus
from agno.run.agent import RunOutput
from agno.tools.yfinance import YFinanceTools
from tenacity import retry_if_exception, stop_after_attempt, wait_exponential, retry

from invesetment_agent.application.exceptions import AgentExecutionError, MultiAgentExecutionError
from invesetment_agent.application.port.ai_agent_service import AgentService


class FallbackAgnoAgentService(AgentService):

    def __init__(self, agent_services: List[AgentService]):
        self.agent_services: List[AgentService] = agent_services or []

    def get_answer(self, query: str, instructions: List[str]) -> str:
        agent_errors: List[AgentExecutionError] = []
        for agent_service in self.agent_services:
            try:
                answer = agent_service.get_answer(query, instructions)
                if answer:
                    return answer
            except AgentExecutionError as e:
                agent_errors.append(e)

        raise MultiAgentExecutionError(errors=agent_errors)


class FinancialAgnoAgentService(AgentService):

    def __init__(self, model: Model):
        self.model: Model = model

    @staticmethod
    def is_rate_limit_error(exception):
        """Returns True if the exception contains a 429 or Resource Exhausted message."""
        error_msg = str(exception)
        return "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg

    @retry(
        retry=retry_if_exception(is_rate_limit_error),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=15, min=30, max=60),
        reraise=True
    )
    def get_answer(self,
                   query: str,
                   instructions: Optional[Union[str, List[str]]] = None):
        agent: Agent = Agent(
            model=self.model,
            tools=[
                YFinanceTools()
            ],
            debug_mode=True,
            name="Investment Analyst",
            description="Researches stock prices, analyst recommendations, and stock fundamentals.",
            instructions=instructions,
        )

        run: RunOutput = agent.run(
            query,
            stream=False,
        )
        if run.status == RunStatus.error:
            raise AgentExecutionError(message=run.content, name=agent.name, )
        return run.content
