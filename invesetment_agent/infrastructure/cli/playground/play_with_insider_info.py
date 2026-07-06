import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from agno.agent import Agent
from agno.db import BaseDb
from agno.db.sqlite import SqliteDb
from agno.models.base import Model
from agno.models.google import Gemini
from agno.skills import LocalSkills, Skills
from agno.tools.python import PythonTools
from agno.tools.yfinance import YFinanceTools
from dotenv import load_dotenv
from edgar import Company, set_identity
from edgar.entity import EntityFilings
from edgar.ownership import Form4

# Buckets you asked for, in days
_BUCKETS = [("3 months", 90)]
# Sale codes (S = open-market sale, D = disposition to issuer)
_SELL_CODES = {"S", "D"}

skills_path: Path = Path(__file__).parent.parent / "skills"
skills_path.mkdir(exist_ok=True, parents=True)


# @tool(description="Get insider (SEC Form 4) buy/sell activity for a stock ticker, "
#                   "broken down by time window, with CEO flagging and % of holdings sold.")
def get_insider_activity(
    ticker: str,
) -> pd.DataFrame:
    company = Company(ticker)

    today = datetime.today()
    # Pull the widest window once (90 days) and bucket in memory
    start = (today - timedelta(days=365)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    filings: EntityFilings = company.get_filings(form="4", filing_date=(start, end))
    dataframes = []
    for filing in filings:
        f4: Form4 = filing.obj()
        df = f4.to_dataframe()
        dataframes.append(df)

    # Concatenate them vertically (stacking them on top of each other)
    combined_df = pd.concat(dataframes, ignore_index=True)
    return combined_df


def create_model() -> Model:
    env_path: Path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)

    # Setup database for storage
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise RuntimeError("GOOGLE_API_KEY not set in environment. Please set it (e.g., in .env).")

    return Gemini(
        # id="gemini-2.5-flash-lite",
        id="gemini-3.1-pro-preview",
        api_key=google_api_key,
    )


def create_finance_agent(model: Model, db: BaseDb) -> Agent:
    from edgar.ai import install_skill

    install_skill(
        to=skills_path,
    )
    return Agent(
        name="Finance Agent",
        role="Get financial data",
        model=model,
        skills=Skills(
            loaders=[
                LocalSkills(path=f"{skills_path}", validate=False),
            ]
        ),
        tools=[
            PythonTools(),
            YFinanceTools(
                # stock_price=True,
                # analyst_recommendations=True,
                # company_info=True, company_news=True
            ),
        ],
        instructions=[
            "For insider/ownership questions, use the EdgarTools skill.",
            "Call get_skill_instructions(skill_name='EdgarTools'), then "
            "get_skill_reference(skill_name='EdgarTools', reference_path=...) to read the ownership/Form 4 API.",
            "'ownership' is a reference INSIDE the EdgarTools skill, not a separate skill.",
            "Then WRITE and EXECUTE edgartools Python using the python tool to fetch the data. "
            "Remember to set_identity(...) before calling edgar.",
            "Always present results as tables.",
        ],
        db=db,
        add_history_to_context=True,
        markdown=True,
    )


def main():
    # agent_os.serve(app="finance_agent_team:app", reload=True,)
    financial_query = """
        for TSLA stock,

    Can you get the detail of CEO buying/selling stock within 3 months, 1 month, 1 week, 24 hours.
    other than CEO, can you get the same info of insider transaction for the same time ranges.
    can you get the selling stocks percentage too?
        """
    model: Model = create_model()
    db = SqliteDb(db_file="agents.db")
    finance_agent = create_finance_agent(model, db)
    finance_agent.print_response(
        financial_query,
        stream=False,
    )


if __name__ == "__main__":
    os.environ["EDGAR_IDENTITY"] = "your.email@example.com"
    set_identity("your.email@example.com")
    # main()

    # Set pandas options to ensure complete content is captured (though to_markdown handles much of it)
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_colwidth", None)

    tesla: pd.DataFrame = get_insider_activity("TSLA")
    print("\nTesla Insider Activity:")
    print(tesla.to_markdown(index=False, tablefmt="grid"))

    amazon: pd.DataFrame = get_insider_activity("AMZN")
    print("\nAmazon Insider Activity:")
    print(amazon.to_markdown(index=False, tablefmt="grid"))

    apple: pd.DataFrame = get_insider_activity("AAPL")
    print("\nApple Insider Activity:")
    print(apple.to_markdown(index=False, tablefmt="grid"))
    #
