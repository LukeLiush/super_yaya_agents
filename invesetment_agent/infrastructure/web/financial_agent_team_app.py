import os

import boto3
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.aws import AwsBedrock
from agno.os import AgentOS
from agno.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools

from invesetment_agent.infrastructure.utils import set_kb_bedrock_aws_credentials_env_variables

set_kb_bedrock_aws_credentials_env_variables()
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_session_token = os.getenv("AWS_SESSION_TOKEN")
aws_region = os.getenv("AWS_REGION", "us-east-1")
session_kwargs = {
    "aws_access_key_id": aws_access_key,
    "aws_secret_access_key": aws_secret_key,
    "aws_session_token": aws_session_token,
    "region_name": aws_region,
}
boto_session = boto3.Session(**session_kwargs)

# Setup database for storage
db = SqliteDb(db_file="agents.db")
model=AwsBedrock(
        id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        aws_region=aws_region,
        session=boto_session,
        max_tokens=1024,
        temperature=0.7,
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
        YFinanceTools()
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
    markdown=True,
)

agent_os = AgentOS(agents=agent_team.members)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="financial_agent_team_app:app", reload=True)
