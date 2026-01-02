from abc import abstractmethod
from typing import List, Union

from agno.agent import Agent
from agno.team import Team

from invesetment_agent.application.port.ai_agent_service import AgentService


class AgnoAgentService(AgentService):

    def get_answer(self, query: str, instructions: List[str]) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_agent(self) -> Union[Agent | Team]:
        raise NotImplementedError
