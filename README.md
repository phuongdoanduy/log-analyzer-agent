# Log Analyzer Agent

GCP log analysis and incident investigation agent built on **Google ADK** (Agent Development Kit).

## What It Does

- **Fetches logs** from GCP Cloud Logging using `gcloud` CLI
- **Analyzes errors** — groups similar errors, identifies patterns, severity breakdown
- **Generates reports** — structured investigation reports with findings and recommendations
- **Multi-environment** — supports dev-vn, dev, test, performance, prod

## Architecture

```
User Request → param_gatherer → log_fetcher → log_analyzer → report_composer → report_saver
```

5-agent pipeline orchestrated by ADK's `SequentialAgent`.

## Quick Start

```bash
# Install dependencies
uv sync

# Run locally
agents-cli playground

# Or quick test
agents-cli run "analyze errors in dev-vn last 2 hours"
```

## Prerequisites

- Python 3.11+
- gcloud CLI installed and authenticated
- Google API key (for Gemini)

```bash
# Setup gcloud
gcloud auth login --update-adc
gcloud config set project YOUR_PROJECT_ID

# Setup API key
cp .env.example .env
# Add GOOGLE_API_KEY to .env
```

## GCP Environment Map

| Env | GCP Project | Cluster | Region |
|-----|-------------|---------|--------|
| dev-vn | klara-nonprod | klara-dev-vn | asia-southeast1-a |
| dev | klara-nonprod | klara-nonprod | europe-west6-a |
| test | klara-nonprod | klara-nonprod | europe-west6-a |
| performance | klara-performance | klara-performance | europe-west6-a |
| prod | klara-prod | klara-prod | europe-west6-a |

## Commands

```bash
# Development
agents-cli playground              # Interactive testing
agents-cli run "your prompt"       # Quick smoke test

# Evaluation
agents-cli eval run                # Full eval (generate + grade)
agents-cli eval generate           # Run inference
agents-cli eval grade              # Score traces

# Deployment (when ready)
agents-cli scaffold enhance . --deployment-target agent_runtime
agents-cli deploy
```

## MCP Integration (Optional)

The agent supports MCP integration with `polaris-mcp-server` for skill-based tools. See `app/agent.py` for configuration.

## Project Structure

```
log-analyzer-agent/
├── app/
│   ├── agent.py          # Multi-agent pipeline definition
│   ├── config.py         # GCP environment map, configuration
│   └── fast_api_app.py   # FastAPI server for ADK
├── tests/
│   └── eval/
│       ├── datasets/     # Eval datasets
│       └── eval_config.yaml
├── docs/
│   └── architecture.md   # Architecture diagram and docs
├── CLAUDE.md             # Claude Code guidance
├── AGENTS.md             # Coding agent guidance
└── README.md
```

## License

MIT
