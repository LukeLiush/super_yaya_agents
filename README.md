# Super Yaya Agents

This repository contains various AI agents and tools.

## Projects

- [Finance Report](./finance_report/README.md): A DDD-based finance reporting tool with Inngest background jobs.
- [Investment Agent](./invesetment_agent/README.md): AI-driven investment analysis and team.

## Prerequisites

- Python 3.11+
- `uv` for dependency management.
- Node.js (for some infrastructure tools).

## Getting Started

```bash
uv sync
```

## CLI Usage

The project includes a command-line interface named `yaya` for interacting with the finance report services.

### Prerequisites
The CLI communicates with the Finance Report Web API. Ensure the web server is running. (Note: The server entry point should be confirmed, typically it would be `finance_report.reporting_core.infrastructure.web.inngest_fns` or similar).

### Setup
If you haven't installed the package, you can run the CLI using `uv run`:
```bash
uv run yaya --help
```
Or directly via module:
```bash
uv run python -m finance_report.reporting_core.infrastructure.cli.yaya --help
```

### Finance Commands

#### Trigger a Report
Generate reports for a specific ticker. You can specify which types of reports to generate using flags.
```bash
# Trigger only price report (default if no flags provided)
uv run yaya finance trigger TSLA --price

# Trigger only insider report
uv run yaya finance trigger TSLA --insider

# Trigger both price and insider reports
uv run yaya finance trigger TSLA --price --insider

# Trigger all available reports
uv run yaya finance trigger TSLA --all
```

#### Show Report Results
Display the results of a generated report.
```bash
uv run yaya finance show <REPORT_ID>
```

#### Check Report Status
Check the generation status of a report.
```bash
uv run yaya finance status <REPORT_ID>
```
