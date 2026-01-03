from pathlib import Path


def load_instruction(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"Error: {path} not found."


current_file_dir = Path(__file__).resolve().parent
