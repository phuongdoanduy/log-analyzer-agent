# CLAUDE.md — Log Analyzer Agent

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Project Overview

**log-analyzer-agent** is a GCP log analysis and incident investigation agent built on Google ADK (Agent Development Kit). It fetches logs from GCP Cloud Logging, analyzes errors, and produces structured investigation reports.

## Commands

### Backend (Python ADK)

```bash
# Install dependencies
uv sync

# Run the ADK API server
adk api_server --port 8000

# Quick smoke test
agents-cli run "analyze errors in dev-vn last 2 hours"

# Interactive playground
agents-cli playground

# Run tests
pytest

# Lint
agents-cli lint
```

### Evaluation

```bash
# Run full eval (generate + grade)
agents-cli eval run

# Two-step eval
agents-cli eval generate
agents-cli eval grade

# Compare results
agents-cli eval compare baseline.json candidate.json
```

## Architecture

### Agent Pipeline

`app/agent.py` defines a 5-agent pipeline:

```
log_analyst_coordinator (LlmAgent) — root agent, understands user request
└── log_analysis_pipeline (SequentialAgent)
    ├── param_gatherer        → extracts env, severity, freshness from request
    ├── log_fetcher           → calls gcloud logging read, saves to JSON
    ├── log_analyzer          → groups errors, finds patterns, severity breakdown
    ├── report_composer       → generates markdown investigation report
    └── report_saver          → saves report to plans/reports/
```

### Key ADK Patterns Used

- **`output_key`** — agents communicate via session state keys
- **`BuiltInPlanner`** — enabled on log_analyzer for extended reasoning
- **`after_agent_callback`** — `collect_errors_callback` deduplicates errors across passes
- **`include_contents="none"`** — report_composer doesn't see raw chat history
- **`BaseAgent` subclass** — `PreflightChecker` for gcloud auth verification

### Tools (FunctionTool)

- `verify_gcloud_auth()` — checks gcloud CLI installation and authentication
- `fetch_gcp_logs()` — runs `gcloud logging read` with filters
- `analyze_log_file()` — parses JSON logs, groups errors by pattern
- `save_report()` — saves markdown report to disk

### MCP Integration (Optional)

The agent supports MCP integration with `polaris-mcp-server` for skill-based tools:
- `gcloud-setup` — gcloud auth verification skill
- `gcp-fetch-logs` — log fetching skill
- `log-analysis` — analysis methodology skill
- `root-cause-report` — report template skill

To enable MCP, uncomment the `McpToolset` configuration in `app/agent.py`.

### Configuration

`app/config.py` contains:
- GCP environment map (dev-vn, dev, test, performance, prod)
- Model configuration
- Default analysis parameters
- MCP server settings

### Scoring Model

Severity levels:
- CRITICAL: System down, data loss
- ERROR: Functionality broken, errors in logs
- WARNING: Potential issues, degraded performance
- INFO/DEBUG: Informational

Report severity:
- critical: >50 errors
- high: >20 errors
- medium: >5 errors
- low: ≤5 errors
