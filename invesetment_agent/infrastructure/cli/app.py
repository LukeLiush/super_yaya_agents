import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from invesetment_agent.application.dtos.commons import Result
from invesetment_agent.application.dtos.stock_summarization_dtos import SingleStockSummarizationRequest, \
    MultiStockSummarizationRequest
from invesetment_agent.infrastructure.config.container import Application
from invesetment_agent.infrastructure.config.container import create_application

# Load environment variables - try project root first, then current directory
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / ".env"
if not env_path.exists():
    load_dotenv(verbose=True)  # Fallback to current working directory
else:
    load_dotenv(dotenv_path=env_path, verbose=True)
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#super-yaya")


def get_slack_client() -> WebClient:
    """Get a Slack WebClient instance."""
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN not set in environment")
    return WebClient(token=SLACK_BOT_TOKEN)


def resolve_channel_id(channel: str, slack_client: WebClient) -> str:
    """Convert channel name to ID if needed."""
    if channel.startswith("#"):
        try:
            response = slack_client.conversations_list()
            for ch in response["channels"]:
                if ch["name"] == channel[1:]:
                    return ch["id"]
        except SlackApiError:
            pass
    return channel


def post_to_slack(channel: str, text: str, thread_ts: str = None) -> str:
    """Post a message to a Slack channel. Returns the message timestamp."""
    slack_client = get_slack_client()
    channel_id = resolve_channel_id(channel, slack_client)
    
    try:
        response = slack_client.chat_postMessage(
            channel=channel_id,
            text=text,
            thread_ts=thread_ts,
        )
        return response["ts"]
    except SlackApiError as e:
        raise RuntimeError(f"Failed to post to Slack: {e.response['error']}")


def main():
    app: Application = create_application()
    stock_summarization_use_case = app.stock_summarization_use_case
    
    # Define stocks to analyze
    stocks = [
        SingleStockSummarizationRequest("vtsax"),
        # Add more stocks here as needed
        # SingleStockSummarizationRequest("vbtlx"),
    ]
    
    # Get current datetime in PST timezone
    pst_time = datetime.now(ZoneInfo("America/Los_Angeles"))
    datetime_str = pst_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    # Create stock symbols string
    stock_symbols = " ".join([stock.stock.upper() for stock in stocks])
    
    # Post initial message with datetime and stock symbols
    initial_message = f"{datetime_str} stock {stock_symbols}"
    thread_ts = post_to_slack(SLACK_CHANNEL, initial_message)
    
    # Execute stock summarization and post results as thread replies
    result: Result = stock_summarization_use_case.execute(MultiStockSummarizationRequest(stocks))
    
    if result.is_success:
        # Post the summary as a thread reply
        post_to_slack(SLACK_CHANNEL, result.value, thread_ts=thread_ts)
    else:
        error = result.error
        error_message = f"❌ *Error processing stocks*\n*Code:* {error.code.value}\n*Message:* {error.message}"
        if error.details:
            error_message += f"\n*Details:* {error.details}"
        post_to_slack(SLACK_CHANNEL, error_message, thread_ts=thread_ts)


if __name__ == "__main__":
    main()
