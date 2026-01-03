from agno.agent import Agent
from agno.db import BaseDb
from agno.db.base import AsyncBaseDb
from agno.models.base import Model
from agno.run import RunStatus
from agno.run.agent import RunOutput
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.hackernews import HackerNewsTools
from agno.tools.reddit import RedditTools

from invesetment_agent.application.exceptions import AgentExecutionError
from invesetment_agent.infrastructure.adapter.agno_financial_team.agno_agent import AgnoAgentService
from invesetment_agent.infrastructure.adapter.agno_financial_team.utils import current_file_dir, load_instruction

news_sentiment_rules = load_instruction(current_file_dir / "instructions" / "news_sentiment_instructions.md")


class AgnoNewsSentimentAgent(AgnoAgentService):
    def get_agent(self):
        return self.web_agent

    def __init__(self, model: Model, db: BaseDb | AsyncBaseDb | None = None):
        self.web_agent = Agent(
            name="News_Sentiment_Agent",
            role="Sentiment Analyst",
            tools=[DuckDuckGoTools(), RedditTools(), HackerNewsTools()],
            model=model,
            db=db,
            instructions=[news_sentiment_rules],
            debug_mode=True,
        )

    def get_answer(self, query: str) -> str:
        run: RunOutput = self.web_agent.run(
            query,
            stream=False,
        )
        content = run.content or ""
        if run.status == RunStatus.error:
            raise AgentExecutionError(message=content, name=run.agent_name or self.web_agent.name or "Unknown")
        return content
