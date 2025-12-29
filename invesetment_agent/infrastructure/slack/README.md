# Slack Bot Deployment Guide

This guide explains how to deploy the Slack bot application to Docker Hub and Render as a free long-running service with CI/CD automation.

## Overview

The Slack bot (`app.py`) is a Socket Mode application that listens for Slack events and responds to stock analysis requests. It's containerized using Docker and automatically deployed via GitHub Actions.

## Architecture

```
GitHub Push → GitHub Actions → Build Docker Image → Push to Docker Hub → Render Pulls & Deploys
```

## Prerequisites

1. **Docker Hub Account**: Create an account at [hub.docker.com](https://hub.docker.com)
2. **Render Account**: Create a free account at [render.com](https://render.com)
3. **GitHub Repository**: Your code repository with GitHub Actions enabled

## Step 1: Set Up Docker Hub Secrets in GitHub

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add the following secrets:

   | Secret Name | Description | How to Get |
   |-------------|-------------|------------|
   | `DOCKER_HUB_USERNAME` | Your Docker Hub username | Your Docker Hub account username |
   | `DOCKER_HUB_TOKEN` | Docker Hub access token | Docker Hub → Account Settings → Security → New Access Token |

### Creating Docker Hub Access Token

1. Log in to [Docker Hub](https://hub.docker.com)
2. Click on your profile → **Account Settings**
3. Go to **Security** → **New Access Token**
4. Give it a name (e.g., "github-actions")
5. Set permissions to **Read & Write**
6. Copy the token and add it to GitHub Secrets as `DOCKER_HUB_TOKEN`

## Step 2: GitHub Actions Workflow

The workflow file `.github/workflows/docker-build-push.yml` is already configured to:

- Trigger on pushes to `main` branch (or specific file changes)
- Build the Docker image
- Push to Docker Hub as `your-username/super-yaya-slack-bot:latest`

### Workflow Triggers

The workflow triggers on:
- Push to `main` branch
- Changes to Slack app code, application code, config, or Dockerfile
- Manual trigger via `workflow_dispatch`

## Step 3: Set Up Render Service

### 3.1 Create a New Web Service

1. Log in to [Render Dashboard](https://dashboard.render.com)
2. Click **New +** → **Web Service**
3. Connect your GitHub repository (or use Docker Hub)

### 3.2 Configure Docker Hub Deployment

**Option A: Deploy from Docker Hub (Recommended)**

1. Select **Docker Hub** as the source
2. Enter your Docker image: `your-username/super-yaya-slack-bot:latest`
3. Set the following:

   **Basic Settings:**
   - **Name**: `super-yaya-slack-bot`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: (leave empty)
   - **Runtime**: `Docker`
   - **Docker Image Path**: `your-username/super-yaya-slack-bot:latest`
   - **Docker Command**: (leave empty, uses Dockerfile CMD)

   **Advanced Settings:**
   - **Auto-Deploy**: `Yes` (automatically pulls new images)
   - **Health Check Path**: `/health` (optional, if you add a health endpoint)

### 3.3 Configure Environment Variables

Add the following environment variables in Render:

| Variable | Description | Required |
|----------|-------------|----------|
| `SLACK_APP_TOKEN` | Slack App-Level Token (starts with `xapp-`) | Yes |
| `SLACK_BOT_TOKEN` | Slack Bot User OAuth Token (starts with `xoxb-`) | Yes |
| `GOOGLE_API_KEY` | Google Gemini API key | Yes |
| `OPENROUTER_API_KEY` | OpenRouter API key (optional) | No |
| `DEEPSEEK_API_KEY` | DeepSeek API key (optional) | No |
| `GROK_API_KEY` | Groq API key (optional) | No |
| `HF_API_KEY` | HuggingFace API key (optional) | No |

### 3.4 Render Free Tier Configuration

For the **Free** tier:
- **Instance Type**: Free
- **Auto-Deploy**: Enabled
- **Health Check**: Optional (can add a simple health endpoint)

**Note**: Free tier services spin down after 15 minutes of inactivity. For a Slack bot that needs to be always-on, consider:
- Using Render's paid tier ($7/month for always-on)
- Or using a different free service like Railway, Fly.io, or Heroku

## Step 4: Verify Deployment

1. **Check GitHub Actions**: Go to Actions tab and verify the workflow runs successfully
2. **Check Docker Hub**: Verify the image appears in your Docker Hub repository
3. **Check Render Logs**: In Render dashboard, check the service logs for:
   - "Bot is running!" message
   - No error messages
4. **Test Slack Bot**: Mention the bot or send a test message

## Step 5: Auto-Deploy on Render

Render's free tier supports auto-deploy from Docker Hub:

1. In Render service settings, enable **Auto-Deploy**
2. Render will periodically check Docker Hub for new images
3. When a new image is pushed, Render will automatically pull and deploy it

**Note**: For faster deployments, you can manually trigger a deploy in Render dashboard after GitHub Actions completes.

## CI/CD Flow

```
1. Developer pushes code to GitHub
   ↓
2. GitHub Actions workflow triggers
   ↓
3. Docker image is built
   ↓
4. Image is pushed to Docker Hub
   ↓
5. Render detects new image (or manual deploy)
   ↓
6. Render pulls and deploys new image
   ↓
7. Slack bot restarts with new code
```

## Troubleshooting

### Docker Build Fails

- Check GitHub Actions logs for specific errors
- Verify `Dockerfile` syntax
- Ensure all dependencies are in `pyproject.toml`

### Image Not Pushing to Docker Hub

- Verify `DOCKER_HUB_USERNAME` and `DOCKER_HUB_TOKEN` secrets are set correctly
- Check Docker Hub token has write permissions
- Verify Docker Hub username matches the repository name

### Render Deployment Fails

- Check Render logs for errors
- Verify environment variables are set correctly
- Ensure Docker image path is correct: `username/repository:tag`
- Check that Render can access Docker Hub (public images)

### Bot Not Responding

- Check Render service is running (not spun down)
- Verify `SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN` are correct
- Check Render logs for connection errors
- Verify Slack app is configured for Socket Mode

## Manual Deployment

If you need to manually deploy:

```bash
# Build locally
docker build -t your-username/super-yaya-slack-bot:latest .

# Push to Docker Hub
docker login
docker push your-username/super-yaya-slack-bot:latest

# Then trigger deploy in Render dashboard
```

## Cost Considerations

- **GitHub Actions**: Free for public repos, 2000 minutes/month for private
- **Docker Hub**: Free for public repos, 1 private repo free
- **Render**: Free tier available, but services spin down after inactivity
  - For always-on: $7/month per service
  - Alternative: Use Railway ($5/month) or Fly.io (free tier with limits)

## Security Best Practices

1. Never commit secrets to the repository
2. Use GitHub Secrets for sensitive data
3. Use Render's environment variables for runtime secrets
4. Rotate API keys and tokens periodically
5. Use Docker Hub access tokens instead of passwords
6. Enable Docker Hub 2FA for additional security

## Next Steps

- Add health check endpoint to the Slack app
- Set up monitoring and alerts
- Configure log aggregation
- Add deployment notifications

