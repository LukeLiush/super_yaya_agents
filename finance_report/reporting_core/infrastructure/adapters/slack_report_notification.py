import json
import logging

from agno.tools.slack import SlackTools

from ...application.ports.report_notification import ReportNotifier, NotificationThread

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
        return NotificationThread(ref=response_data["ts"], )

    async def post_report(self, thread: NotificationThread, slack_message: str) -> None:
        self._slack_tools.send_message_thread(channel=self._slack_channel, text=slack_message, thread_ts=thread.ref)
