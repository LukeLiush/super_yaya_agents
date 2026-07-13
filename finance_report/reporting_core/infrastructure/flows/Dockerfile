FROM python:3.11-slim

ENV APP_HOME=/app
ENV PYTHONPATH=/app
WORKDIR /app

RUN pip install --no-cache-dir uv

# workspace metadata + lock
COPY pyproject.toml uv.lock ./

# copy the member code FIRST so uv can see the workspace member
COPY finance_report/ ./finance_report/

# now sync: installs deps (prefect, etc.); --no-install-project skips building your package
RUN uv sync --frozen --no-dev --package finance-report --no-install-project

ENV PATH="/app/.venv/bin:$PATH"
