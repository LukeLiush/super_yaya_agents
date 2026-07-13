import json
import logging

from agno.tools.slack import SlackTools

from finance_report.reporting_core.application.ports.report_notification import NotificationThread, ReportNotifier

logger = logging.getLogger(__name__)


class SlackReportNotifier(ReportNotifier):
    def __init__(self, slack_tools: SlackTools, slack_channel: str):
        self._slack_tools: SlackTools = slack_tools
        self._slack_channel: str = slack_channel

    async def open_thread(self, subject: str) -> NotificationThread | None:
        response_json: str = self._slack_tools.send_message(self._slack_channel, subject)
        response_data = json.loads(response_json)
        if "ts" not in response_data:
            logger.error(f"Failed to start Slack thread: {response_json}")
            return None
        return NotificationThread(
            ref=response_data["ts"],
        )

    async def post_report(self, thread: NotificationThread, slack_message: str) -> None:
        self._slack_tools.send_message_thread(channel=self._slack_channel, text=slack_message, thread_ts=thread.ref)


async def main():
    # 1. Properly instantiate the notifier
    notifier = SlackReportNotifier(
        slack_tools=SlackTools(token=os.environ["SLACK_BOT_TOKEN"]),
        slack_channel="#super-yaya"
    )

    # 2. Await the async method call
    thread = await notifier.open_thread("test notification")

    if thread:
        print(f"Successfully opened thread with ref: {thread.ref}")
        # Optionally test posting a report
        await notifier.post_report(thread, "This is a test report message")
    else:
        print("Failed to open thread")


if __name__ == "__main__":
    print("test")
    from dotenv import load_dotenv

    load_dotenv()
    import os
    import asyncio

    asyncio.run(main())
