# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**log-analyzer-agent** is a GCP log analysis and incident investigation agent built on Google ADK (Agent Development Kit). It fetches logs from GCP Cloud Logging, analyzes errors, and produces structured investigation reports.

## Commands

### Setup

```bash
# Install dependencies
uv sync

# For eval dependencies
uv sync --extra eval

# For lint dependencies
uv sync --extra lint
```

### Running

```bash
# Interactive playground (ADK web UI)
adk web

# ADK API server
adk api_server --port 8000

# FastAPI server directly
uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000

# Quick smoke test
agents-cli run "analyze errors in dev-vn last 2 hours"
```

### Tests

```bash
# All unit tests
pytest tests/unit/

# Single test
pytest tests/unit/test_dummy.py::test_dummy -v

# Integration tests (starts FastAPI server internally)
pytest tests/integration/

# All tests
pytest
```

### Lint

```bash
# Run all linters (ruff + ty + codespell)
agents-cli lint

# Or individually
uv run ruff check .
uv run ty check .
uv run codespell .
```

### Evaluation

```bash
# Full eval (generate + grade)
agents-cli eval run

# Two-step
agents-cli eval generate
agents-cli eval grade

# Compare baselines
agents-cli eval compare baseline.json candidate.json
```

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Gemini API access |
| `LOGS_BUCKET_NAME` | No | GCS bucket for OTel telemetry upload |
| `ALLOW_ORIGINS` | No | Comma-separated CORS origins for FastAPI |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | No | Set to `NO_CONTENT` to enable telemetry |

Copy `.env.example` to `.env` and add `GOOGLE_API_KEY`.

## Architecture

### Agent Pipeline

`app/agent.py` defines the full pipeline. All agents run on `gemini-2.0-flash` (`config.worker_model`).

```
log_analyst_coordinator (LlmAgent)           — root agent, user-facing coordinator
└── log_analysis_pipeline (SequentialAgent)
    ├── param_gatherer   output_key="analysis_params"   → resolves env→project, severity, freshness
    ├── log_fetcher      output_key="fetch_result"      → runs gcloud logging read
    ├── log_analyzer     output_key="log_analysis"      → groups errors, calls collect_errors_callback
    ├── report_composer  output_key="investigation_report" → Markdown report, calls build_report_callback
    └── report_saver     output_key="save_result"       → writes to plans/reports/
```

### Session State Flow

Agents communicate exclusively via session state keys (`output_key`). The chain is:
- `analysis_params` → consumed by log_fetcher and report_composer
- `fetch_result` → consumed by log_analyzer and report_composer
- `log_analysis` → consumed by report_composer; also aggregated into `all_errors` by `collect_errors_callback`
- `investigation_report` → processed by `build_report_callback` into `final_report`
- `final_report` + `analysis_params` → consumed by report_saver

### Key ADK Patterns

- **`output_key`** — sole mechanism for inter-agent data passing; no direct agent-to-agent calls
- **`BuiltInPlanner`** — enabled only on `log_analyzer` for extended thinking during pattern analysis
- **`include_contents="none"`** — set on `report_composer` and `report_saver` to prevent them from seeing raw chat history (they read only from state)
- **`after_agent_callback`** — `collect_errors_callback` deduplicates errors into `all_errors`; `build_report_callback` computes severity and builds the final report header
- **`_EvalSequentialAgent`** — thin `SequentialAgent` subclass that adds `instruction` and `tools` fields required by the ADK eval harness
- **`PreflightChecker`** — `BaseAgent` subclass that calls `verify_gcloud_auth()` directly (no LLM); escalates via `EventActions(escalate=True)` if auth fails

### Tools (FunctionTool)

All tools are pure functions wrapped with `FunctionTool(...)`:

- `verify_gcloud_auth()` → checks gcloud CLI installation and active auth
- `fetch_gcp_logs(project, severity, freshness, service_filter, limit, output_file)` → runs `gcloud logging read`, saves JSON to `/tmp/gcp_logs.json`
- `analyze_log_file(log_file)` → groups errors by first 100 chars of message, returns top 20 groups
- `save_report(report_content, env, output_dir)` → saves Markdown to `plans/reports/log-analysis-{env}-{timestamp}.md`

### Configuration (`app/config.py`)

Single `LogAnalyzerConfig` dataclass instantiated as `config` singleton. Add new environments to `env_map`. Severity scoring thresholds live in `build_report_callback` in `agent.py`:
- `critical` → >50 errors
- `high` → >20 errors
- `medium` → >5 errors
- `low` → ≤5 errors

### FastAPI Server (`app/fast_api_app.py`)

Wraps ADK's `get_fast_api_app` with:
- OTel telemetry via `setup_telemetry()` (logs to GCS if `LOGS_BUCKET_NAME` set)
- Artifact storage pointing to `gs://{LOGS_BUCKET_NAME}` when configured
- `POST /feedback` endpoint for user feedback collection via Google Cloud Logging

### MCP Integration (Optional)

Commented-out `McpToolset` in `agent.py` connects to `polaris-mcp-server` for skill-based tools. To enable, uncomment the `polaris_mcp` block and wire it into the relevant agents.

### Eval

Eval datasets live in `tests/eval/datasets/`. Config in `tests/eval/eval_config.yaml` defines three custom metrics: `env_resolution_accuracy`, `report_completeness`, `no_hallucinated_errors`.
