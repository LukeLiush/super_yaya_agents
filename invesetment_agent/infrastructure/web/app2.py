import streamlit as st
from contextlib import AbstractContextManager
from typing import cast

st.write("🟢 STREAMLIT PAGE IS WORKING! 🟢")
st.title("AI Investment Agent 📈🤖")
st.caption("This app allows you to compare the performance of two stocks and generate detailed reports.")

st.write("Loading dependencies...")

import os
import boto3

from agno.agent import Agent
from agno.models.aws import AwsBedrock
from agno.run.agent import RunOutput
from agno.tools.yfinance import YFinanceTools

from invesetment_agent.infrastructure.utils import set_kb_bedrock_aws_credentials_env_variables

print("Streamlit app is starting...")
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

assistant = Agent(
    model=AwsBedrock(
        id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        aws_region=aws_region,
        session=boto_session,
        max_tokens=1024,
        temperature=0.7,
    ),
    tools=[
        YFinanceTools(
            # stock_price=True,
            # analyst_recommendations=True,
            # stock_fundamentals=True,
        )
    ],
    debug_mode=True,
    description="You are an investment analyst that researches stock prices, analyst recommendations, and stock fundamentals.",
    instructions=[
        "Format your response using markdown and use tables to display data where possible."
    ],
)

col1, col2 = st.columns(2)
with col1:
    stock1 = st.text_input("Enter first stock symbol (e.g. AAPL)")
with col2:
    stock2 = st.text_input("Enter second stock symbol (e.g. MSFT)")

if stock1 and stock2:
    with st.spinner(f"Analyzing {stock1} and {stock2}..."): # ignore
        query = f"Compare both the stocks - {stock1} and {stock2} and make a detailed report for an investment trying to invest and compare these stocks"
        response: RunOutput = assistant.run(query, stream=False)
        st.markdown(response.content)
