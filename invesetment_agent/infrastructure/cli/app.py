import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from invesetment_agent.application.dtos.commons import Result
from invesetment_agent.application.dtos.stock_summarization_dtos import (
    MultiTickerSummarizationRequest,
    SingleTickerSummarizationRequest,
)
from invesetment_agent.infrastructure.config.container import Application, create_application

# Load environment variables - try project root first, then current directory
current_file_dir = Path(__file__).resolve().parent
env_path = current_file_dir / ".env"
if not env_path.exists():
    load_dotenv(verbose=True)  # Fallback to current working directory
else:
    load_dotenv(dotenv_path=env_path, verbose=True)
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")
SLACK_USER_EMAIL_MENTION = os.getenv("SLACK_USER_EMAIL_MENTION")


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
                    return str(ch["id"])
        except SlackApiError:
            pass
    return channel


class SlackUserConverter:
    """Converts email addresses to Slack user IDs."""

    def __init__(self, slack_client: WebClient | None = None):
        """
        Initialize the converter with a Slack client.

        Args:
            slack_client: Optional Slack WebClient. If not provided, will create one.
        """
        self._slack_client = slack_client or get_slack_client()

    def convert(self, email: str) -> str | None:
        """
        Convert an email address to a Slack user ID.

        Args:
            email: The email address to look up.

        Returns:
            The Slack user ID if found, None otherwise.
        """
        try:
            response = self._slack_client.users_lookupByEmail(email=email)
            if response["ok"] and "user" in response:
                return str(response["user"]["id"])
        except SlackApiError as e:
            # User not found or other API error
            if e.response.get("error") != "users_not_found":
                # Log other errors if needed, but return None for any error
                pass
        return None


def post_to_slack(channel: str, text: str, thread_ts: str | None = None) -> str:
    """Post a message to a Slack channel. Returns the message timestamp."""
    slack_client: WebClient = get_slack_client()
    channel_id: str = resolve_channel_id(channel, slack_client)

    response = slack_client.chat_postMessage(
        channel=channel_id,
        text=text,
        thread_ts=thread_ts,
    )
    return str(response["ts"])


def main() -> None:
    app: Application = create_application()
    stock_summarization_use_case = app.stock_summarization_use_case

    # Define stocks to analyze
    stocks = [
        SingleTickerSummarizationRequest("VTSAX"),
        # sAdd more stocks here as needed
        # SingleTickerSummarizationRequest("VBTLX"),
        # SingleTickerSummarizationRequest("FNMA"),
        # SingleTickerSummarizationRequest("TSLA"),
        SingleTickerSummarizationRequest("AMZN"),
    ]

    # Get current datetime in PST timezone
    pst_time = datetime.now(ZoneInfo("America/Los_Angeles"))
    # Format datetime in a more readable, Slack-friendly way
    date_str = pst_time.strftime("%B %d, %Y")  # e.g., "January 15, 2024"
    time_str = pst_time.strftime("%I:%M %p %Z")  # e.g., "10:30 AM PST"

    # Create stock symbols string
    stock_symbols = " ".join([stock.ticker.upper() for stock in stocks])

    # Create catchy, Slack-friendly initial message
    initial_message: str = f"📊 *Daily Stock Analysis* | {date_str} at {time_str}\nAnalyzing: {stock_symbols}\n"
    if SLACK_USER_EMAIL_MENTION:
        emails = SLACK_USER_EMAIL_MENTION.split()
        user_ids = [SlackUserConverter().convert(email) for email in emails]
        user_tags = [f"<@{user_id}>" for user_id in user_ids if user_id]
        user_tag = " ".join(user_tags)
        initial_message += f"Hey {user_tag}! 👋 Generating insights within thread..."

    if not SLACK_CHANNEL:
        raise ValueError("SLACK_CHANNEL not set in environment")
    thread_ts = post_to_slack(SLACK_CHANNEL, initial_message)

    # Execute stock summarization and post results as thread replies
    for stock in stocks:
        result: Result = stock_summarization_use_case.execute(MultiTickerSummarizationRequest([stock]))
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
