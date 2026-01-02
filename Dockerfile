# Use Python 3.11 slim image as base
FROM python:3.11-slim

# 1. Define the variable once
ENV APP_HOME=/app

# 2. Use that variable to set the WORKDIR
WORKDIR $APP_HOME

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./


RUN uv sync --no-install-project

# Install dependencies using uv
RUN uv sync --frozen

# Copy the application code
COPY . .

# Set the command to run the Slack app
CMD ["sh", "-c", "env | cut -d'=' -f1 && uv run python -m invesetment_agent.infrastructure.slack.app"]

