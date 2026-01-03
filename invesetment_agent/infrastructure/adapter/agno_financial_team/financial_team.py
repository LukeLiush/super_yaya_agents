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
            reasoning=False,
            instructions=[
                "--- ASSET TYPE VALIDATION & ROUTING ---",
                "1. MANDATORY VALIDATION: Use Finance_Agent to identify the ticker's asset type.",
                "   Supported types: [Stock, Equity Fund, Mutual Fund, Index Fund, Bond ETF, Bond Fund].",
                "2. VALIDITY CHECK: If the identified type is not in the supported list above, "
                "stop and inform the user that the asset type is currently unsupported.",
                "3. TEMPLATE SELECTION:",
                f"   - IF STOCK: Use THIS template for Styler: \n{stock_template}\n"
                f"     AND instruct News_Sentiment_Agent with THIS template: \n{news_sentiment_template}",
                f"   - IF EQUITY/MUTUAL/INDEX FUND: Use THIS template for Styler: \n{equity_fund_template}",
                f"   - IF BOND ETF: Use THIS template for Styler: \n{bond_etf_template}",
                f"   - IF BOND FUND: Use THIS template for Styler: \n{bond_fund_template}",
                "4. FINAL AUDIT: Verify that Slack_Styler followed the selected template exactly. "
                "MANDATORY: Every output MUST start with the title: 📡 *Daily [Asset Type] Intelligence: [COMPANY/FUND NAME] ($[TICKER])*. "
                "CRITICAL: The final output MUST be a plain text message for Slack. "
                "STRICTLY FORBIDDEN: JSON structures, standard Markdown (like **Bold**), or internal reasoning logs. "
                "DATA AVAILABILITY: If certain metrics are missing, ensure the report still includes all other available data. Do not skip the entire report.",
                leader_rules,
            ],
            debug_mode=True,
            markdown=True,
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
