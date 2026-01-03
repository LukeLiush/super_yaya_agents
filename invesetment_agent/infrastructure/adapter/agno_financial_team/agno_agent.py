from abc import abstractmethod

from agno.agent import Agent
from agno.team import Team

from invesetment_agent.application.port.ai_agent_service import AgentService


class AgnoAgentService(AgentService):
    def get_answer(self, query: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_agent(self) -> Agent | Team:
        raise NotImplementedError
