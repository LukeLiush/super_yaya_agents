# Capabilities + UnsupportedCapability
from pydantic import BaseModel


class Capabilities(BaseModel):
    """A plugin's honest self-description. The core reads this to decide
       what operations to allow/offer, rather than assuming uniformity."""
    can_reschedule: bool  # can the backend change a cron in place?
    can_pause: bool
    can_cancel_run: bool
    can_poll_status: bool  # False => status() may return UNKNOWN
    supports_scheduling: bool  # False => core must own the schedule itself

    def require(self, capability: str) -> None:
        if not getattr(self, capability, False):
            raise UnsupportedCapability(capability)


class UnsupportedCapability(Exception):
    pass
