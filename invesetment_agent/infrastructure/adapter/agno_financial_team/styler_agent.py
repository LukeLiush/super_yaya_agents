from typing import Optional, Union, List

from agno.agent import Agent
from agno.db import BaseDb
from agno.db.base import AsyncBaseDb
from agno.models.base import Model
from agno.run import RunStatus
from agno.run.agent import RunOutput
from agno.team import Team

from invesetment_agent.application.exceptions import AgentExecutionError
from invesetment_agent.infrastructure.adapter.agno_financial_team.agno_agent import AgnoAgentService
from invesetment_agent.infrastructure.adapter.agno_financial_team.utils import current_file_dir, load_instruction

finance_rules = load_instruction(current_file_dir / "instructions" / "finance_agent_instructions.md")


class AgnoStylerAgent(AgnoAgentService):
    def get_agent(self) -> Union[Agent | Team]:
        return self.styler_agent

    def __init__(self,
                 model: Model,
                 db: Optional[Union[BaseDb, AsyncBaseDb]] = None):
        self.styler_agent = Agent(
            name="Slack_Styler",
            role="Designer",
            description="Transforms data into Slack-formatted reports using analogies.",
            model=model,
            db=db,
            instructions=["Wait for the Team Leader to provide the specific MD template based on asset type."]
        )

    def get_answer(self, query: str, instructions: List[str]) -> str:
        run: RunOutput = self.styler_agent.run(
            query,
            stream=False,
        )
        if run.status == RunStatus.error:
            raise AgentExecutionError(message=run.content, name=run.name, )
        return run.content
