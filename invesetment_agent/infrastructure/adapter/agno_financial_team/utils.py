from pathlib import Path
from agno.tools import tool


def load_instruction(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"Error: {path} not found."


current_file_dir = Path(__file__).resolve().parent


@tool()
def get_instruction_content(instruction_name: str) -> str:
    """
    Load the content of a specific instruction or template file.
    Use this to get the rules or templates for different asset types or agent roles.

    Args:
        instruction_name: The name of the instruction file (e.g., 'styler_stock_instructions.md', 'team_leader_instructions.md').

    Returns:
        The content of the instruction file as a string.
    """
    instructions_path = current_file_dir / "instructions" / instruction_name
    return load_instruction(instructions_path)
