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

## Prefect Setup and Orchestration

This project supports **Prefect** as an alternative orchestrator to Inngest.

### 1. Configuration (Switching to Prefect)

The project uses a settings-based approach to determine which orchestrator to use. To point the orchestrator to Prefect:
- In your `.env` file, set:
  ```env
  ORCHESTRATOR=prefect
  ```
- Alternatively, you can change the default in `finance_report/reporting_core/infrastructure/config/settings.py` (though `.env` is preferred).
- When `ORCHESTRATOR=prefect`, the system uses `PrefectASGI` to handle report triggers, which queues runs on your Prefect deployment.

### 2. Local Testing with Prefect

#### A. Start the Prefect Server
Before running the local worker or triggering reports, you need a running Prefect instance. In a new terminal, run:
```bash
uv run prefect server start
```
This will start the Prefect dashboard at `http://localhost:4200`.

#### B. Local Worker and Secret Sync
Once the server is up, run the local serve script in another terminal:
```bash
uv run python finance_report/reporting_core/infrastructure/flows/local_prefect_serve.py
```
This script will:
1.  Automatically sync your local secrets (from `.env`) to Prefect Blocks.
2.  Start a local worker that listens for flow runs.

#### C. Triggering Reports
With both the server and the local worker running, you can trigger reports via the CLI or API, and they will be executed by the local worker.

### 3. Remote Deployment (Docker + Prefect Cloud/Server)

To deploy the flow to a remote Prefect server (e.g., Prefect Cloud or a self-hosted instance):

1.  **Configure API URL**: Ensure `PREFECT_API_URL` is set to your remote server address.
2.  **Deploy**: Use the provided deployment script:
    ```bash
    uv run python finance_report/reporting_core/infrastructure/flows/remote_prefect_deploy.py
    ```
3.  **What this script does**:
    - It builds a Docker image using the `Dockerfile` located at `finance_report/reporting_core/infrastructure/flows/Dockerfile`.
    - It pushes the image to Docker Hub (defaulting to `ethankulakula/super-yaya-slack-bot`).
    - It registers the deployment on the Prefect server using the `my-docker-pool` work pool.

### Triggering via API
When Prefect is enabled, you can still use the standard trigger endpoint. The request will be automatically routed to Prefect:
```bash
curl -X POST http://127.0.0.1:8000/report/trigger -H "Content-Type: application/json" -d '{"ticker": "TSLA", "report_types": ["price"]}'
```
The response will contain a Prefect flow run URL for tracking.

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
*   **Prefect ASGI Adapter:** `finance_report/reporting_core/infrastructure/web/prefect_asgi.py`
*   **Prefect Local Serve:** `finance_report/reporting_core/infrastructure/flows/local_prefect_serve.py`
*   **Prefect Remote Deploy:** `finance_report/reporting_core/infrastructure/flows/remote_prefect_deploy.py`
*   **DI Container:** `finance_report/reporting_core/infrastructure/config/container.py`
*   **Domain Models:** `finance_report/reporting_core/domain/`
*   **Persistence:** `finance_report/reporting_core/infrastructure/persistence/`
