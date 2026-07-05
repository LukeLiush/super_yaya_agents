from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class NotificationThread:
    # opaque to the domain; adapter knows it's a Slack ts
    ref: str


class ReportNotifier(Protocol):
    async def open_thread(self, subject: str) -> NotificationThread | None: ...

    async def post_report(self, thread: NotificationThread, slack_message: str) -> None: ...
