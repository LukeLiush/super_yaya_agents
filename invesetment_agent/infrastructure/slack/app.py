from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from invesetment_agent.application.dtos.stock_summarization_dtos import SingleEquitySummarizationRequest, \
    MultiEquitySummarizationRequest
from invesetment_agent.infrastructure.config.container import Application, create_application

env_path: Path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
# Null check (Validation)
missing_vars = []
if not SLACK_APP_TOKEN:
    missing_vars.append("SLACK_APP_TOKEN")
if not SLACK_BOT_TOKEN:
    missing_vars.append("SLACK_BOT_TOKEN")

if missing_vars:
    # Print to stderr so it stands out in logs
    print(f"ERROR: Missing environment variables: {', '.join(missing_vars)}", file=sys.stderr)
    print("Ensure these are set in the Railway 'Variables' tab.", file=sys.stderr)
    # Stop the app immediately
    sys.exit(1)

print("Environment variables loaded successfully.")

app = App(token=SLACK_BOT_TOKEN)


@app.event("app_mention")
def handle_mention(event, say):
    """Respond when bot is mentioned"""
    user = event['user']
    text = event['text']

    # Simple response
    say(f"Hi <@{user}>! You said: {text}")


@app.message("yaya_stock_daily_digest")
def handle_stock_daily_digest(message, say):
    """Respond to 'hello' messages"""
    thread_ts = message["ts"]
    say(f"Wait for one sec!", thread_ts=thread_ts)

    text = message.get('text', '')
    symbols = set(text.split("\n")[0].split()[1:])

    invalid_stocks: List[SingleEquitySummarizationRequest] = []
    valid_stocks: List[SingleEquitySummarizationRequest] = []
    for symbol in symbols:
        stock_request = SingleEquitySummarizationRequest(symbol)
        if stock_request.is_valid():
            valid_stocks.append(stock_request)
        else:
            invalid_stocks.append(stock_request)

    if valid_stocks:
        say(f"valid symbols: {', '.join([valid_stock.equity for valid_stock in valid_stocks])}",
            thread_ts=thread_ts)
    else:
        say("❌ *No valid stock symbols found!*\n\n*Usage:* `yaya_stock_daily_digest AAPL TSLA MSFT GOOGL AMZN",
            thread_ts=thread_ts)

    app: Application = create_application()
    stock_summarization_use_case = app.stock_summarization_use_case

    for valid_stock in valid_stocks:
        stock_result = stock_summarization_use_case.execute(MultiEquitySummarizationRequest([valid_stock]))
        say(f"*{valid_stock.equity}*\n{stock_result.value}", thread_ts=thread_ts)


if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()  # This line makes @app.event handlers run
    print("Bot is running!")
