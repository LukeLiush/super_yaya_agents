from agno.agent import Agent
from agno.models.base import Model
from agno.run import RunStatus
from agno.run.agent import RunOutput

from invesetment_agent.application.exceptions import AgentExecutionError, MultiAgentExecutionError
from invesetment_agent.application.port.ai_agent_service import AgentService


class FinancialAgnoAgentService(AgentService):
    def __init__(self, model: Model):
        self.agent = Agent(
            name="Financial_Agent",
            model=model,
            instructions=["Provide financial analysis based on the user's query."],
        )

    def get_answer(self, query: str) -> str:
        run: RunOutput = self.agent.run(query, stream=False)
        content = run.content or ""
        if run.status == RunStatus.error:
            raise AgentExecutionError(message=content, name=run.agent_name or self.agent.name or "Unknown Agent")
        return content


class FallbackAgnoAgentService(AgentService):
    def __init__(self, agent_services: list[AgentService]):
        self.agent_services: list[AgentService] = agent_services or []

    def get_answer(self, query: str) -> str:
        agent_errors: list[AgentExecutionError] = []
        for agent_service in self.agent_services:
            try:
                answer = agent_service.get_answer(query)
                if answer:
                    return answer
            except AgentExecutionError as e:
                agent_errors.append(e)

        raise MultiAgentExecutionError(errors=agent_errors)
