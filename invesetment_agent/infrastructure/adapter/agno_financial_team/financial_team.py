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
from invesetment_agent.infrastructure.adapter.agno_financial_team.utils import (
    get_instruction_content,
    load_instruction,
)

current_file_dir = Path(__file__).resolve().parent
instructions_path = current_file_dir / "instructions"
leader_rules = load_instruction(instructions_path / "team_leader_instructions.md")


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
            tools=[get_instruction_content],
            reasoning=False,
            instructions=[
                "--- ASSET TYPE VALIDATION & ROUTING ---",
                "1. MANDATORY VALIDATION: Use Finance_Agent to identify the ticker's asset type.",
                "   Supported types: [Stock, Equity Fund, Mutual Fund, Index Fund, Bond ETF, Bond Fund].",
                "2. VALIDITY CHECK: If the identified type is not in the supported list above, "
                "stop and inform the user that the asset type is currently unsupported.",
                "3. TEMPLATE SELECTION (DYNAMIC LOADING):",
                "   Use the `get_instruction_content` tool to load the appropriate template for each agent:",
                "   - IF STOCK: Load 'styler_stock_instructions.md' for Styler AND 'news_sentiment_instructions.md' for News_Sentiment_Agent.",
                "   - IF EQUITY/MUTUAL/INDEX FUND: Load 'styler_equity_fund_instructions.md' for Styler.",
                "   - IF BOND ETF: Load 'styler_bond_etf_instructions.md' for Styler.",
                "   - IF BOND FUND: Load 'styler_bond_fund_instructions.md' for Styler.",
                "4. FINAL AUDIT: Verify that Slack_Styler followed the selected template exactly. ",
                "MANDATORY: Every output MUST start with the title: 📡 *Daily [Asset Type] Intelligence: [COMPANY/FUND NAME] ($[TICKER])*. ",
                "CRITICAL: The final output MUST be a plain text message for Slack. ",
                "STRICTLY FORBIDDEN: JSON structures, standard Markdown (like **Bold**), or internal reasoning logs. ",
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
