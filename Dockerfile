# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

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
# Note: Socket Mode doesn't require HTTP port, but Render may need a process to keep running
CMD ["uv", "run", "python", "-m", "invesetment_agent.infrastructure.slack.app"]

