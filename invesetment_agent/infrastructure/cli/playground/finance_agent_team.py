import os

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.google import Gemini
from agno.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

# Setup database for storage
db = SqliteDb(db_file="agents.db")
google_api_key = os.environ.get("GOOGLE_API_KEY")
if not google_api_key:
    raise RuntimeError("GOOGLE_API_KEY not set in environment. Please set it (e.g., in .env).")

model = Gemini(
    id="gemini-3-pro-preview",
    api_key=google_api_key,
)
web_agent = Agent(
    name="Web Agent",
    role="Search the web for information",
    model=model,
    tools=[DuckDuckGoTools()],
    db=db,
    add_history_to_context=True,
    markdown=True,
)

finance_agent = Agent(
    name="Finance Agent",
    role="Get financial data",
    model=model,
    tools=[
        YFinanceTools(
            # stock_price=True,
            # analyst_recommendations=True,
            # company_info=True, company_news=True
        )
    ],
    instructions=["Always use tables to display data"],
    db=db,
    add_history_to_context=True,
    markdown=True,
)

agent_team = Team(
    name="Agent Team (Web+Finance)",
    model=model,
    members=[web_agent, finance_agent],
    debug_mode=True,
    reasoning=True,  # Enables the internal 'thinking' steps
    stream=True,  # Tells the server to push data as it's generated
    markdown=True,
)

# agent_os = AgentOS(teams=[agent_team])
# app = agent_os.get_app()

if __name__ == "__main__":
    # agent_os.serve(app="finance_agent_team:app", reload=True,)
    query = """
    for Amzn and TESLA stock,

Can you get the detail of CEO buying/selling stock within 3 months, 1 month, 1 week, 24 hours.
other than CEO, can you get the same info of insider transation for the same time ranges.
can you get the selling stocks percentage too?
    """
    agent_team.run(
        query,
        stream=False,
    )
