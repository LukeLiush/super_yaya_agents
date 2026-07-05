# Finance Report

This project is a family finance report tool built using Domain-Driven Design (DDD) principles. It fetches market data (from yfinance), news, and insider transactions to generate comprehensive company reports.

## Build / Configuration

This project uses `uv` for dependency management and execution.

### Prerequisites
- Install `uv` (if not already installed).
- Node.js (for `inngest-cli`).

### Setup

```bash
uv sync
```

## Running the Inngest Web Server

The project uses **FastAPI** to serve Inngest functions and provide a trigger endpoint.

### 1. Start the Inngest Dev Server
Inngest requires a separate Dev Server to orchestrate events and retries locally.
```bash
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
```
*Note: This command points the Inngest Dev Server to your Python application's Inngest endpoint.*

### 2. Start the Python Web Server
Open a new terminal and start the FastAPI application using `uvicorn`. 

**Note for local development:** The app defaults to local development mode (`is_production=False`). In this mode, no Inngest Signing Key is required.

```bash
uv run python -m uvicorn finance_report.reporting_core.infrastructure.web.api_routes:app --reload
```
The server will start at `http://127.0.0.1:8000`.

**Note for production:** If you need to run in production mode, set the following environment variables:
```bash
export INNGEST_IS_PRODUCTION=true
export INNGEST_SIGNING_KEY=your_key_here
```

---

## Yaya CLI Usage

The `yaya` CLI is the primary way to interact with the finance report services from the command line.

### 1. Triggering Reports (`trigger`)

The `trigger` command is the primary way to start a new analysis.

```bash
# Trigger ALL available reports (default behavior if no flags provided)
uv run yaya finance trigger TSLA

# Trigger only the PRICE report
uv run yaya finance trigger TSLA --price

# Trigger only the INSIDER report
uv run yaya finance trigger TSLA --insider

# Trigger MULTIPLE specific reports
uv run yaya finance trigger TSLA --price --insider
```

*   **How it works**: The ticker (`TSLA`) is a required argument. The flags (`--price`, `--insider`) are dynamic. If you add a new report type to the `ReportType` enum in `schemas.py`, the CLI will automatically support it as a flag (e.g., `--valuation`) without changing the CLI code.

### 2. Checking Status and Results

Once a report is triggered, you receive a **Report ID**. You can use this ID to track or view the report.

```bash
# Check the status of a specific report generation
uv run yaya finance status <REPORT_ID>

# Show the results of a completed report
uv run yaya finance show <REPORT_ID>
```

*Note: Currently, `status` and `show` are structural placeholders in the CLI.*

### 3. Help and Discovery

The CLI is self-documenting. You can always check available commands and dynamic flags:

```bash
# General help
uv run yaya --help

# Finance sub-command help
uv run yaya finance --help

# Trigger command help (displays all current dynamic flags)
uv run yaya finance trigger --help
```

---

## Alternative Testing Methods

### Method A: Using the Trigger Endpoint
We've provided a helper endpoint to easily request a report for a specific ticker:
```bash
# Example: Trigger a price report for Apple (AAPL)
curl -X POST http://127.0.0.1:8000/trigger/AAPL
```
You should see a message: `{"message": "Price report requested for AAPL"}`.

### Method B: Using the Inngest Dev Server UI
1.  Open your browser to the Inngest Dev Server UI (usually `http://127.0.0.1:8288`).
2.  Go to the **"Events"** tab.
3.  Send a new event with:
    *   **Event Name:** `app/report.requested`
    *   **Payload:** `{"ticker": "MSFT", "report_types": ["price"]}`
4.  You can watch the function execution logs in the **"Functions"** or **"Runs"** tab.

### Method C: Health Check
Verify the FastAPI server is running:
```bash
curl http://127.0.0.1:8000/health
```
Response: `{"status": "ok"}`

## Testing

### Running tests
```bash
uv run pytest
```

## Project Structure
*   **CLI Entry Point:** `finance_report/reporting_core/infrastructure/cli/yaya.py`
*   **Web Entry Point:** `finance_report/reporting_core/infrastructure/web/api_routes.py`
*   **Inngest Functions:** `finance_report/reporting_core/infrastructure/web/inngest_fns.py`
*   **DI Container:** `finance_report/reporting_core/infrastructure/config/container.py`
*   **Domain Models:** `finance_report/reporting_core/domain/`
*   **Persistence:** `finance_report/reporting_core/infrastructure/persistence/`
