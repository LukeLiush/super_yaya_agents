import os
from pathlib import Path

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


def post_to_slack(channel: str, text: str) -> None:
    """Post a message to a Slack channel."""
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN not set in environment")
    
    slack_client = WebClient(token=SLACK_BOT_TOKEN)
    
    # Convert channel name to ID if needed
    if channel.startswith("#"):
        try:
            response = slack_client.conversations_list()
            for ch in response["channels"]:
                if ch["name"] == channel[1:]:
                    channel = ch["id"]
                    break
        except SlackApiError:
            pass
    
    try:
        slack_client.chat_postMessage(
            channel=channel,
            text=text,
        )
    except SlackApiError as e:
        raise RuntimeError(f"Failed to post to Slack: {e.response['error']}")


def main():
    app: Application = create_application()
    stock_summarization_use_case = app.stock_summarization_use_case
    vtsax = SingleStockSummarizationRequest("vtsax")
    # vtsax.instructions.append("Format your response using markdown and use tables to display data where possible")
    result: Result = stock_summarization_use_case.execute(MultiStockSummarizationRequest([vtsax]))
    
    if result.is_success:
        message = f"*{vtsax.stock}*\n{result.value}"
    else:
        error = result.error
        message = f"❌ *Error processing {vtsax.stock}*\n*Code:* {error.code.value}\n*Message:* {error.message}"
        if error.details:
            message += f"\n*Details:* {error.details}"
    
    post_to_slack(SLACK_CHANNEL, message)
    # vbtlx = SingleStockSummarizationRequest("vbtlx")
    # stock_summarization_use_case.execute(vbtlx)


if __name__ == "__main__":
    main()
