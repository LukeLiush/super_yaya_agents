from pathlib import Path
from typing import Optional, Union, List

from agno.agent import Agent
from agno.db import BaseDb
from agno.db.base import AsyncBaseDb
from agno.models.base import Model
from agno.run import RunStatus
from agno.run.team import TeamRunOutput
from agno.team import Team

from invesetment_agent.application.exceptions import AgentExecutionError
from invesetment_agent.infrastructure.adapter.agno_financial_team.utils import load_instruction, current_file_dir
from invesetment_agent.infrastructure.adapter.agno_financial_team.agno_agent import AgnoAgentService

finance_rules = load_instruction(current_file_dir / "instructions" / "finance_agent_instructions.md")

current_file_dir = Path(__file__).resolve().parent
instructions_path = current_file_dir / "instructions"
leader_rules = load_instruction(instructions_path / "team_leader_instructions.md")
stock_template = load_instruction(instructions_path / "styler_stock_instructions.md")
equity_fund_template = load_instruction(instructions_path / "styler_equity_fund_instructions.md")
bond_etf_template = load_instruction(instructions_path / "styler_bond_etf_instructions.md")
bond_fund_template = load_instruction(instructions_path / "styler_bond_fund_instructions.md")


class AgnoFinancialTeam(AgnoAgentService):
    def get_agent(self) -> Union[Agent | Team]:
        return self.team_leader

    def __init__(self,
                 agno_agent_services: List[AgnoAgentService],
                 model: Model,
                 db: Optional[Union[BaseDb, AsyncBaseDb]] = None):
        self.team_leader = Team(
            name="Investment_Team_Leader",
            members=[agno_agent_service.get_agent() for agno_agent_service in agno_agent_services],
            model=model,
            db=db,
            instructions=
            [
                "--- DYNAMIC ROUTING LOGIC ---",
                "Step 1: Use Finance_Agent to determine the ticker type. Supported types: Stock, Equity Fund, Mutual Fund, Index Fund, Bond ETF, Bond Fund.",
                "Step 1a: Validate the ticker type. If the detected type is NOT one of the supported types, raise a warning: Ticker type unknown. Please verify input.",
                f"Step 2: IF STOCK -> Instruct Styler to use THIS template: \n{stock_template}",
                f"Step 3: IF EQUITY FUND, MUTUAL FUND, or INDEX FUND -> Instruct Styler to use THIS template: \n{equity_fund_template}",
                f"Step 4: IF BOND ETF -> Instruct Styler to use THIS template: \n{bond_etf_template}",
                f"Step 5: IF BOND FUND -> Instruct Styler to use THIS template: \n{bond_fund_template}",
                "Step 6: Audit the output. Ensure single-asterisk bolding (*Text*) and ASCII tables in ``` blocks.",
            ] + [leader_rules],
            debug_mode=True,
            markdown=False,
        )

    def get_answer(self, query: str, instructions: List[str]) -> str:
        run: TeamRunOutput = self.team_leader.run(
            query,
            stream=False,
        )
        if run.status == RunStatus.error:
            raise AgentExecutionError(message=run.content, name=run.team_name, )
        return run.content
