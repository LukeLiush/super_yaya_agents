"""
AI Data Analyst — complete runnable example using Prefect + pydantic-ai.

Setup:
    pip install "pydantic-ai[prefect]" pandas
    export OPENAI_API_KEY="sk-..."          # macOS/Linux
    # setx OPENAI_API_KEY "sk-..."          # Windows

Run (quick local test, no server needed):
    python ai_data_analyst.py

Run with full UI/observability:
    prefect server start          # in one terminal -> http://localhost:4200
    python ai_data_analyst.py     # in another terminal
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from prefect import flow, task
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.durable_exec.prefect import PrefectAgent, TaskConfig

env_path: Path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

google_api_key = os.environ.get("GOOGLE_API_KEY")
if not google_api_key:
    raise RuntimeError("GOOGLE_API_KEY not set in environment. Please set it (e.g., in .env).")


# --------------------------------------------------------------------------
# Agent tools — plain Python functions. Each becomes its own Prefect task,
# so they get independent retries, caching, and show up in the UI.
# The dataframe is injected via ctx.deps (typed as pd.DataFrame below).
# --------------------------------------------------------------------------
def get_column_info(ctx: RunContext[pd.DataFrame]) -> dict[str, Any]:
    """Overview of all columns — helps the agent understand structure first."""
    df = ctx.deps
    return {
        "columns": list(df.columns),
        "rows": len(df),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }


def calculate_statistics(ctx: RunContext[pd.DataFrame], column: str) -> dict[str, Any]:
    """Descriptive stats for a numeric column."""
    df = ctx.deps
    if column not in df.columns:
        return {"error": f"Column '{column}' not found. Available: {list(df.columns)}"}
    # describe() returns numpy types; cast so the result is JSON-serializable
    stats = df[column].describe().to_dict()
    return {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in stats.items()}


def detect_anomalies(ctx: RunContext[pd.DataFrame], column: str, threshold: float = 3.0) -> list[dict[str, Any]]:
    """Flag values more than `threshold` standard deviations from the mean."""
    df = ctx.deps
    if column not in df.columns:
        return [{"error": f"Column '{column}' not found"}]
    if not pd.api.types.is_numeric_dtype(df[column]):
        return [{"error": f"Column '{column}' is not numeric"}]

    mean, std = df[column].mean(), df[column].std()
    if std == 0:
        return []

    anomalies = df[abs(df[column] - mean) > (threshold * std)]
    return [
        {
            "index": int(idx),
            "value": float(row[column]),
            "z_score": float((row[column] - mean) / std),
        }
        for idx, row in anomalies.head(10).iterrows()
    ]


# --------------------------------------------------------------------------
# Structured output — the LLM's answer is validated into this Pydantic model.
# --------------------------------------------------------------------------
class DataAnalysis(BaseModel):
    """Structured, validated output."""

    summary: str
    key_findings: list[str] = Field(min_length=3, max_length=5)
    recommendations: list[str] = Field(min_length=3, max_length=5)
    columns_analyzed: list[str]

    def __str__(self) -> str:
        findings = "\n".join(f"  {i}. {f}" for i, f in enumerate(self.key_findings, 1))
        recs = "\n".join(f"  {i}. {r}" for i, r in enumerate(self.recommendations, 1))
        return (
            f"\n{'=' * 70}\nANALYSIS RESULTS\n{'=' * 70}\n"
            f"\nSummary:\n  {self.summary}\n"
            f"\nKey Findings:\n{findings}\n"
            f"\nRecommendations:\n{recs}\n"
            f"\nColumns Analyzed: {', '.join(self.columns_analyzed)}\n{'=' * 70}\n"
        )


# --------------------------------------------------------------------------
# Build the agent and wrap it for durable execution.
# --------------------------------------------------------------------------
def create_agent() -> PrefectAgent[pd.DataFrame, DataAnalysis]:
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    model = GoogleModel("gemini-2.5-flash-lite", provider=GoogleProvider(api_key=google_api_key))

    agent = Agent(
        model,
        name="data-analyst-agent",
        output_type=DataAnalysis,
        deps_type=pd.DataFrame,
        tools=[get_column_info, calculate_statistics, detect_anomalies],
        system_prompt=(
            "You are an expert data analyst. Always start by calling get_column_info "
            "to understand the dataset, then use calculate_statistics and "
            "detect_anomalies on the numeric columns before drawing conclusions."
        ),
    )
    return PrefectAgent(
        agent,
        model_task_config=TaskConfig(retries=3, retry_delay_seconds=[1.0, 2.0, 4.0], timeout_seconds=60.0),
        tool_task_config=TaskConfig(retries=2, retry_delay_seconds=[0.5, 1.0]),
    )


# --------------------------------------------------------------------------
# Sample data + orchestrating flow.
# --------------------------------------------------------------------------
@task
def create_sample_dataset() -> pd.DataFrame:
    """A small sales dataset with two deliberate anomalies in `sales`."""
    return pd.DataFrame(
        {
            "product": ["Widget", "Gadget", "Doohickey", "Widget", "Gadget"] * 20,
            # last two values (1000, 2000) are anomalies vs. the ~100-200 range
            "sales": [100, 150, 200, 110, 145] * 19 + [100, 150, 200, 1000, 2000],
            "region": ["North", "South", "East", "West", "Central"] * 20,
            "month": [1, 2, 3, 4, 5] * 20,
        }
    )


@flow(name="ai-data-analyst", log_prints=True)
async def analyze_dataset_with_ai() -> DataAnalysis:
    print("Preparing dataset...")
    df = create_sample_dataset()
    print(f"Dataset shape: {df.shape}")

    print("Initializing agent...")
    agent = create_agent()

    print("Running AI analysis...")
    result = await agent.run(
        "Analyze this sales dataset. Identify patterns, anomalies, and provide actionable recommendations.",
        deps=df,
    )

    print(result.output)  # uses the __str__ above
    return result.output


# --------------------------------------------------------------------------
# Entry point.
# --------------------------------------------------------------------------
if __name__ == "__main__":
    # Simplest way to run end-to-end:
    asyncio.run(analyze_dataset_with_ai())
