import uuid
from typing import Callable


def _safe_label(text: str, max_len: int = 50) -> str:
    """Produce a bounded, display-safe label from arbitrary text.

    Returns the text unchanged if within max_len. If it exceeds max_len,
    truncates to max_len and appends a short unique suffix so the label
    stays bounded, readable, and distinct.
    """
    if not text:
        return uuid.uuid4().hex[:8]
    if len(text) <= max_len:
        return text
    return f"{text[:max_len]}…-{uuid.uuid4().hex[:8]}"


def run_name_from(extract: Callable[[dict], str], prefix: str = "", max_len: int = 50):
    """Build a Prefect task_run_name callable.

    `extract` receives the task's runtime parameters (a dict) and returns the
    text to turn into a label.
    """

    def _name() -> str:
        from prefect.runtime import task_run
        text = extract(task_run.parameters)
        label = _safe_label(text, max_len)
        return f"{prefix}: {label}".strip()

    return _name
