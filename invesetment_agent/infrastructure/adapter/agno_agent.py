from typing import Optional, List, Union

from agno.agent import Agent
from agno.models.base import Model
from agno.run.agent import RunOutput
from agno.tools.yfinance import YFinanceTools

from invesetment_agent.application.port.ai_agent_service import SingleAgentService


class AgnoAgentService(SingleAgentService):

    def __init__(self, model: Model, role: str, description: str):
        self.model: Model = model
        self.role: str = role
        self.description: str = description

    def get_answer(self,
                   query: str,
                   instructions: Optional[Union[str, List[str]]] = None):
        agent: Agent = Agent(
            model=self.model,
            tools=[
                YFinanceTools()
            ],
            debug_mode=True,
            name=self.role,
            description=self.description,
            instructions=instructions,
        )

        run: RunOutput = agent.run(
            query,
            stream=False,
        )
        return run.content
