# AGENTS.md — Log Analyzer Agent

This file provides guidance to coding agents (VS Code Copilot, Codex, etc.) when working in this repository.

## Project Overview

**log-analyzer-agent** is a GCP log analysis agent built on Google ADK. It fetches logs from GCP Cloud Logging, analyzes errors, and produces investigation reports.

## Commands

```bash
# Install
uv sync

# Run locally
agents-cli playground
agents-cli run "analyze errors in dev-vn last 2 hours"

# Evaluate
agents-cli eval run

# Deploy (when ready)
agents-cli deploy
```

## Architecture

5-agent pipeline: `param_gatherer → log_fetcher → log_analyzer → report_composer → report_saver`

- `app/agent.py` — Agent definitions and pipeline
- `app/config.py` — GCP environment map and configuration
- `tests/eval/` — Evaluation datasets and config

## Key Files

| File | Purpose |
|------|---------|
| `app/agent.py` | Multi-agent pipeline, tools, callbacks |
| `app/config.py` | GCP env map, model config |
| `tests/eval/datasets/basic-dataset.json` | Eval cases |
| `tests/eval/eval_config.yaml` | Eval metrics config |
| `docs/architecture.md` | Architecture diagram |

## GCP Environments

dev-vn → klara-nonprod (asia-southeast1-a)
dev → klara-nonprod (europe-west6-a)
test → klara-nonprod (europe-west6-a)
performance → klara-performance (europe-west6-a)
prod → klara-prod (europe-west6-a)
