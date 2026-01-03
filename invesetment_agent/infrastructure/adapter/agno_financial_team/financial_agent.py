from agno.agent import Agent
from agno.db import BaseDb
from agno.db.base import AsyncBaseDb
from agno.models.base import Model
from agno.run import RunStatus
from agno.run.agent import RunOutput
from agno.tools.yfinance import YFinanceTools

from invesetment_agent.application.exceptions import AgentExecutionError
from invesetment_agent.application.external_service.sec_tools import build_insider_table
from invesetment_agent.infrastructure.adapter.agno_financial_team.agno_agent import AgnoAgentService
from invesetment_agent.infrastructure.adapter.agno_financial_team.utils import current_file_dir, load_instruction

finance_rules = load_instruction(current_file_dir / "instructions" / "finance_agent_instructions.md")


class AgnoFinancialAgent(AgnoAgentService):
    def get_agent(self):
        return self.finance_agent

    def __init__(self, model: Model, db: BaseDb | AsyncBaseDb | None = None):
        self.finance_agent = Agent(
            name="Finance_Agent",
            role="Data Provider",
            tools=[YFinanceTools(), build_insider_table],
            model=model,
            db=db,
            instructions=[finance_rules.format(insider_tool_name=build_insider_table.name)],
            debug_mode=True,
        )

    def get_answer(self, query: str) -> str:
        run: RunOutput = self.finance_agent.run(
            query,
            stream=False,
        )
        content = run.content or ""
        if run.status == RunStatus.error:
            raise AgentExecutionError(
                message=content,
                name=run.agent_name or self.finance_agent.name or "Unknown",
            )
        return content
