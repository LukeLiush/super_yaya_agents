import os
from pathlib import Path

from agno.agent import Agent
from agno.models.google import Gemini
from agno.os import AgentOS
from agno.tools.hackernews import HackerNewsTools
from agno.tools.yfinance import YFinanceTools
from agno.workflow import Step, Workflow
from agno.workflow.parallel import Parallel
from dotenv import load_dotenv

env_path: Path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Setup database for storage
google_api_key = os.environ.get("GOOGLE_API_KEY")
if not google_api_key:
    raise RuntimeError("GOOGLE_API_KEY not set in environment. Please set it (e.g., in .env).")

gemini_model = Gemini(
    id="gemini-2.5-flash-lite",
    api_key=google_api_key,
)

# Two independent researchers — they don't depend on each other
news_researcher = Agent(name="News Researcher",
                        model=gemini_model,
                        tools=[HackerNewsTools()])
finance_researcher = Agent(name="Finance Researcher",
                           model=gemini_model,
                           tools=[YFinanceTools()])

# Downstream steps that depend on the combined research
writer = Agent(name="Writer", model=gemini_model)
reviewer = Agent(name="Reviewer", model=gemini_model)

research_news_step = Step(name="Research News", agent=news_researcher)
research_finance_step = Step(name="Research Finance", agent=finance_researcher)
write_step = Step(name="Write Article", agent=writer)
review_step = Step(name="Review Article", agent=reviewer)

workflow = Workflow(
    name="Content Creation Pipeline",
    steps=[
        # These two run AT THE SAME TIME
        Parallel(research_news_step, research_finance_step, name="Research Phase"),
        # Then the rest run sequentially, receiving BOTH parallel outputs
        write_step,
        review_step,
    ],
)

# if __name__ == "__main__":
#     workflow.print_response(
#         "Write about the latest AI developments and stock trends",
#         markdown=True,
#     )
# --- register it with AgentOS ---
agent_os = AgentOS(
    id="my-os",
    workflows=[workflow],     # <-- the key bit: pass workflows=[...]
)
app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="invesetment_agent.infrastructure.cli.playground.play_with_workflow:app", port=7777)