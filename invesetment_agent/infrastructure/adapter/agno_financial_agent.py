from pathlib import Path
from typing import Optional, Union, List

from agno.agent import Agent
from agno.db import BaseDb
from agno.db.base import AsyncBaseDb
from agno.models.base import Model
from agno.run import RunStatus
from agno.run.team import TeamRunOutput
from agno.team import Team
from agno.tools.yfinance import YFinanceTools

from invesetment_agent.application.exceptions import AgentExecutionError
from invesetment_agent.application.external_service.sec_tools import build_insider_table
from invesetment_agent.application.port.ai_agent_service import AgentService


# --- 1. LOAD INSTRUCTION FILES ---
def load_instruction(path: Path):
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"Error: {path} not found."


current_file_dir = Path(__file__).resolve().parent
instructions_path = current_file_dir / "instructions"
finance_rules = load_instruction(instructions_path / "finance_agent_instructions.md")
leader_rules = load_instruction(instructions_path / "team_leader_instructions.md")
stock_template = load_instruction(instructions_path / "styler_stock_instructions.md")
equity_fund_template = load_instruction(instructions_path / "styler_equity_fund_instructions.md")
bond_etf_template = load_instruction(instructions_path / "styler_bond_etf_instructions.md")
bond_fund_template = load_instruction(instructions_path / "styler_bond_fund_instructions.md")


class AgnoFinancialAgent(AgentService):
    def __init__(self,
                 style_model: Model,
                 finance_model: Model,
                 team_model: Model,
                 db: Optional[Union[BaseDb, AsyncBaseDb]] = None):
        self.style_model: Model = style_model
        self.finance_model: Model = finance_model
        self.team_model: Model = team_model
        self.db: Optional[Union[BaseDb, AsyncBaseDb]] = db

    @classmethod
    def from_single_model(cls,
                          model: Model,
                          db: Optional[Union[BaseDb, AsyncBaseDb]] = None) -> "FinancialAgnoTeamService":
        return cls(style_model=model,
                   finance_model=model,
                   team_model=model,
                   db=db)

    def get_answer(self, query: str, instructions: List[str]) -> str:
        # Tools agent to fetch the raw data
        finance_agent = Agent(
            name="Finance_Agent",
            role="Data Provider",
            tools=[YFinanceTools(), build_insider_table],
            model=self.finance_model,
            instructions=[finance_rules.format(insider_tool_name=build_insider_table.name)],
            debug_mode=True,
        )

        styler_agent = Agent(
            name="Slack_Styler",
            role="Designer",
            description="Transforms data into Slack-formatted reports using analogies.",
            model=self.style_model,
            instructions=["Wait for the Team Leader to provide the specific MD template based on asset type."]
        )

        team_leader = Team(
            name="Investment_Team_Leader",
            members=[finance_agent, styler_agent],
            model=self.team_model,
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
        run: TeamRunOutput = team_leader.run(
            query,
            stream=False,
        )
        if run.status == RunStatus.error:
            raise AgentExecutionError(message=run.content, name=team_leader.name, )
        return run.content
