import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
slack_client = WebClient(token="SLACK_BOT_TOKEN")


def post_to_slack(channel: str, text: str) -> str:
    """Post a message to a Slack channel.

    Args:
        channel (str): Slack channel (e.g. "#super-yaya")
        text (str): Message content
    """
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
        return f"Message successfully posted to {channel}."
    except SlackApiError as e:
        return f"Slack error: {e.response['error']}"


if __name__ == "__main__":
    post_to_slack(channel="#super-yaya", text="World")
