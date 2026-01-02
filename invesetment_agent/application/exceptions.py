from typing import List


class AgentExecutionError(Exception):

    def __init__(self, message: str, name: str = None, cause: Exception = None):
        self.agent_name = name
        self.cause = cause
        base_message = f"[{name}] {message}" if name else message
        if cause:
            base_message += f" | Caused by: {repr(cause)}"
        super().__init__(base_message)


class MultiAgentExecutionError(Exception):
    """Exception raised when multiple agents in a sequence fail."""

    def __init__(self, errors: List[AgentExecutionError]):
        self.errors = errors
        # Basic summary message
        self.message = f"{len(errors)} agents failed to provide an answer."
        super().__init__(self.message)

    def __str__(self):
        # Create a detailed string showing each specific error
        detail_lines = [f"  - {str(e)}" for e in self.errors]
        return f"{self.message}\nDetailed Failures:\n" + "\n".join(detail_lines)
