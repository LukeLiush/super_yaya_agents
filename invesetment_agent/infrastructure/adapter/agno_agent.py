from invesetment_agent.application.exceptions import AgentExecutionError, MultiAgentExecutionError
from invesetment_agent.application.port.ai_agent_service import AgentService


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
