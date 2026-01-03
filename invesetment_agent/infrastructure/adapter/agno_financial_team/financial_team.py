from pathlib import Path

from agno.agent import Agent
from agno.db import BaseDb
from agno.db.base import AsyncBaseDb
from agno.models.base import Model
from agno.run import RunStatus
from agno.run.team import TeamRunOutput
from agno.team import Team

from invesetment_agent.application.exceptions import AgentExecutionError
from invesetment_agent.infrastructure.adapter.agno_financial_team.agno_agent import AgnoAgentService
from invesetment_agent.infrastructure.adapter.agno_financial_team.utils import current_file_dir, load_instruction

finance_rules = load_instruction(current_file_dir / "instructions" / "finance_agent_instructions.md")

current_file_dir = Path(__file__).resolve().parent
instructions_path = current_file_dir / "instructions"
leader_rules = load_instruction(instructions_path / "team_leader_instructions.md")
stock_template = load_instruction(instructions_path / "styler_stock_instructions.md")
equity_fund_template = load_instruction(instructions_path / "styler_equity_fund_instructions.md")
bond_etf_template = load_instruction(instructions_path / "styler_bond_etf_instructions.md")
bond_fund_template = load_instruction(instructions_path / "styler_bond_fund_instructions.md")
news_sentiment_template = load_instruction(instructions_path / "news_sentiment_instructions.md")


class AgnoFinancialTeam(AgnoAgentService):
    def get_agent(self) -> Agent | Team:
        return self.team_leader

    def __init__(
        self, agno_agent_services: list[AgnoAgentService], model: Model, db: BaseDb | AsyncBaseDb | None = None
    ):
        self.team_leader = Team(
            name="Investment_Team_Leader",
            members=[agno_agent_service.get_agent() for agno_agent_service in agno_agent_services],
            model=model,
            db=db,
            instructions=[
                "--- DYNAMIC ROUTING LOGIC ---",
                "Step 1: Use Finance_Agent to determine the ticker type. Supported types: "
                "Stock, Equity Fund, Mutual Fund, Index Fund, Bond ETF, Bond Fund.",
                "Step 1a: Validate the ticker type. If the detected type is NOT one of the supported types, "
                "raise a warning: Ticker type unknown. Please verify input.",
                f"Step 2: IF STOCK -> Instruct Styler to use THIS template: \n{stock_template}",
                f"Step 2a: IF STOCK -> Also instruct News_Sentiment_Agent to provide a sentiment report, "
                f"using THIS template: \n{news_sentiment_template}",
                f"Step 3: IF EQUITY FUND, MUTUAL FUND, or INDEX FUND -> "
                f"Instruct Styler to use THIS template: \n{equity_fund_template}",
                f"Step 4: IF BOND ETF -> Instruct Styler to use THIS template: \n{bond_etf_template}",
                f"Step 5: IF BOND FUND -> Instruct Styler to use THIS template: \n{bond_fund_template}",
                "Step 6: Audit the output. Ensure single-asterisk bolding (*Text*) and ASCII tables in ``` blocks.",
                leader_rules,
            ],
            debug_mode=True,
            markdown=False,
        )

    def get_answer(self, query: str) -> str:
        run: TeamRunOutput = self.team_leader.run(
            query,
            stream=False,
        )
        content = run.content or ""
        if run.status == RunStatus.error:
            raise AgentExecutionError(
                message=content,
                name=run.team_name or "Investment_Team_Leader",
            )
        return content
