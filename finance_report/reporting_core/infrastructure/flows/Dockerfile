# Use Python 3.11 slim image as base
FROM python:3.11-slim

# 1. Define the variable once
ENV APP_HOME=/app
ENV PYTHONPATH=$APP_HOME

# 2. Use that variable to set the WORKDIR
WORKDIR $APP_HOME

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files from the project root
# Note: When building, the context should be the project root
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# --no-install-project avoids installing the project itself in this step
RUN uv sync --frozen --no-install-project

# Copy the finance_report directory
COPY finance_report/ ./finance_report/


# Install the project itself
RUN uv sync --frozen
