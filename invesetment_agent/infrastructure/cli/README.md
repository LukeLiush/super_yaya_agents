# Stock Analysis CLI Application

## Overview

This CLI application (`app.py`) is a scheduled stock analysis tool that automatically generates investment insights for specified stocks and posts them to Slack. It's designed to run as part of a GitHub Actions workflow for automated daily stock analysis.

## Why This CLI is Needed

1. **Automated Daily Analysis**: The CLI enables scheduled, automated stock analysis without manual intervention, providing consistent daily insights at a fixed time (9 AM PST).

2. **Slack Integration**: It automatically posts formatted stock analysis reports directly to Slack channels, making insights easily accessible to your team.

3. **Batch Processing**: The CLI can analyze multiple stocks in a single run, posting each analysis as a threaded reply to maintain organized conversations.

4. **Email-to-User Lookup**: It converts email addresses to Slack user IDs, allowing you to mention team members in notifications using their email addresses.

5. **Scheduled Execution**: Designed to run as part of GitHub Actions workflows, ensuring reliable execution even when local machines are offline.

## Why It's Called by GitHub Actions

The CLI is invoked by the GitHub Actions workflow (`.github/workflows/scheduled-task.yml`) for several reasons:

1. **Reliability**: GitHub Actions provides a reliable, always-on infrastructure that ensures the script runs even when local machines are offline or unavailable.

2. **Scheduled Execution**: GitHub Actions supports cron-based scheduling, allowing the CLI to run automatically at specified times (daily at 9 AM PST).

3. **Secret Management**: GitHub Actions provides secure secret management, allowing sensitive credentials (API keys, tokens) to be stored securely and injected at runtime without exposing them in code.

4. **Consistency**: Running in a standardized environment ensures consistent execution across different runs, regardless of local machine configurations.

5. **Scalability**: GitHub Actions can handle multiple concurrent runs and provides logging and monitoring capabilities.

## Required Environment Variables

The CLI requires the following environment variables to function properly:

### Required Secrets

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key for AI agent | `AIza...` |
| `SLACK_BOT_TOKEN` | Slack bot token for posting messages | `xoxb-...` |
| `SLACK_CHANNEL` | Slack channel ID or name (with #) | `#super-yaya` or `C1234567890` |

### Optional Secrets

| Variable | Description | Example |
|----------|-------------|---------|
| `SLACK_USER_EMAIL_MENTION` | Space-separated email addresses to mention in messages | `user1@example.com user2@example.com` |

### Additional AI Provider Keys (Optional)

The application supports multiple AI providers. You can configure additional keys if you want to use fallback providers. The `FallbackAgnoAgentService` will attempt to use these in order:

- `GOOGLE_API_KEY` - (Primary) For Google Gemini API access
- `OPENROUTER_API_KEY` - For OpenRouter API access
- `DEEPSEEK_API_KEY` - For DeepSeek API access
- `GROK_API_KEY` - For Groq API access
- `HF_API_KEY` - For HuggingFace API access

## Configuring Secrets in GitHub Actions

### Step 1: Access Repository Settings

1. Navigate to your GitHub repository
2. Click on **Settings** (top navigation bar)
3. In the left sidebar, click on **Secrets and variables** → **Actions**

### Step 2: Add a New Secret

1. Click the **New repository secret** button
2. Enter the secret name (e.g., `SLACK_BOT_TOKEN`)
3. Enter the secret value
4. Click **Add secret**

### Step 3: Update the Workflow File

After adding a new secret, you need to update the workflow file to use it:

1. Open `.github/workflows/scheduled-task.yml`
2. Find the step that runs the CLI application (around line 41-47)
3. Add the new secret to the `env:` section:

```yaml
- name: Run investment_agent/infrastructure/cli/app.py
  run:  uv run python -m invesetment_agent.infrastructure.cli.app
  env:
    GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
    SLACK_BOT_TOKEN: ${{ secrets.SLACK_BOT_TOKEN }}
    SLACK_CHANNEL: ${{ secrets.SLACK_CHANNEL }}
    SLACK_USER_EMAIL_MENTION: ${{ secrets.SLACK_USER_EMAIL_MENTION }}
    # Add your new secret here:
    NEW_SECRET_NAME: ${{ secrets.NEW_SECRET_NAME }}
```

### Step 4: Update the CLI Code (if needed)

If the new secret is used in `app.py`, make sure to read it from the environment:

```python
import os
NEW_SECRET = os.getenv("NEW_SECRET_NAME")
```

## Local Development Setup

For local development, create a `.env` file in the project root with your secrets:

```bash
# .env file
GOOGLE_API_KEY=your_google_api_key_here
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL=#super-yaya
SLACK_USER_EMAIL_MENTION=user@example.com
```

**Important**: Never commit the `.env` file to version control. It should be in `.gitignore`.

## How It Works

1. **Initialization**: The CLI loads environment variables and initializes the stock analysis application.

2. **Stock List**: Defines the stocks to analyze (currently configured in `app.py`).

3. **Initial Message**: Posts a formatted message to Slack with:
   - Current date and time (PST)
   - List of stocks being analyzed
   - User mentions (if configured)

4. **Analysis**: For each stock:
   - Executes the stock summarization use case using `SingleTickerSummarizationRequest`
   - Posts the analysis results as a threaded reply to the initial message
   - Handles errors gracefully with formatted error messages

5. **Slack Integration**: Uses the Slack WebClient to:
   - Post messages to specified channels
   - Convert email addresses to Slack user IDs
   - Create threaded conversations for organized discussions

## Schedule

The CLI runs automatically via GitHub Actions:
- **Schedule**: Daily at 9 AM PST (17:00 UTC)
- **Manual Trigger**: Can also be triggered manually via `workflow_dispatch`

## Troubleshooting

### Common Issues

1. **Missing Secrets**: Ensure all required secrets are configured in GitHub Actions
2. **Invalid Slack Token**: Verify the Slack bot token has proper permissions
3. **Channel Not Found**: Check that the Slack channel name/ID is correct
4. **User Not Found**: Verify email addresses in `SLACK_USER_EMAIL_MENTION` are valid Slack user emails

### Testing Locally

To test the CLI locally:

```bash
# Make sure you have a .env file with all required variables
uv run python -m invesetment_agent.infrastructure.cli.app
```

## Security Notes

- All secrets should be stored in GitHub Secrets, never in code
- The `.env` file should never be committed to the repository
- Slack bot tokens should have minimal required permissions
- API keys should be rotated periodically

## Developer Guide: Maintaining the Agno Financial Team

This CLI application uses an AI-powered 'Financial Team' built with the Agno (formerly Phidata) framework. To modify the behavior of the AI agents, follow these guidelines:

### 1. Prompt Organization
- All AI instructions (prompts) are stored as Markdown files in: `invesetment_agent/infrastructure/adapter/agno_financial_team/instructions/`
- **Key files:**
    - `team_leader_instructions.md`: High-level orchestration and routing logic.
    - `news_sentiment_instructions.md`: Specific instructions for the News Sentiment Agent.
    - `styler_stock_instructions.md`: Formatting templates for stock analysis.
    - `finance_agent_instructions.md`: Rules for financial data analysis.

### 2. Modifying Agent Logic
- **Team Structure:** Defined in `invesetment_agent/infrastructure/adapter/agno_financial_team/financial_team.py`. The `AgnoFinancialTeam` class orchestrates multiple sub-agents (Financial, Styler, News Sentiment).
- **Agent Definitions:** Individual agents are defined in their respective files in the same directory (e.g., `news_sentiment_agent.py`, `styler_agent.py`).
- **Adding/Removing Agents:** Update `AgnoFinancialTeam.__init__` and the routing logic in its `instructions`.

### 3. Dependency Injection
- The application is wired together in `invesetment_agent/infrastructure/config/container.py`.
- If you add new agents or services, register them in the `Application` class.

### 4. Testing Changes
- You can test your changes locally by running this CLI:
  ```bash
  uv run python -m invesetment_agent.infrastructure.cli.app
  ```
- Ensure you have the necessary API keys (e.g., `GOOGLE_API_KEY`) in your `.env` file.

