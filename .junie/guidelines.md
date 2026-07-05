# Project Development Guidelines

## Build / Configuration

This project uses `uv` for dependency management and execution.

### Prerequisites
- Install `uv` (if not already installed).

### Setup

uv sync

### Running

uv run
## Testing

### Running tests
uv run pytest


## Additional Development Information

### Code Guidelines (Ponytail Rules)

Write only what the task needs; the best code is the code you never wrote. Before writing any code, stop at the **first** rung that applies:

1. **Does this need to exist?** If no, skip it (YAGNI).
2. **Does the standard library do it?** Use it.
3. **Is there a native platform/language feature?** Use it.
4. **Is there an already-installed dependency?** Use it.
5. **Can it be one line?** Make it one line.
6. **Only then:** write the minimum that works.

**Lazy, not negligent.** The following are *never* cut, regardless of the rungs above: trust-boundary / input validation, data-loss handling, security, and accessibility.

**Mark your shortcuts.** Every shortcut you take must be flagged in the code with a `ponytail:` comment naming its upgrade path, so deferred work doesn't silently become permanent. Example:

    # ponytail: stdlib has one
    from functools import cache

**Reviewing code?** Check the diff for over-engineering and prefer deletion. If a simpler rung was available and skipped without reason, take it.


