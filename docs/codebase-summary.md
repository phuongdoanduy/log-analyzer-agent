# Log Analyzer Agent — Codebase Summary

## Project Overview

**log-analyzer-agent** is a GCP log analysis and incident investigation agent built on Google ADK (Agent Development Kit). It analyzes logs from GCP Cloud Logging to identify error patterns, group similar errors, and generate structured investigation reports for DevOps and SRE teams.

**Tech Stack:** Python 3.11+, Google ADK ≥1.15.0, Gemini 2.0 Flash, FastAPI, uv package manager.

## Directory Structure

```
log-analyzer-agent/
├── app/                                    # Application code
│   ├── agent.py (816 LOC)                  # Multi-agent pipeline and tools
│   ├── config.py                           # Configuration and environment map
│   ├── fast_api_app.py                     # FastAPI server wrapper
│   └── app_utils/
│       ├── telemetry.py                    # OpenTelemetry setup for GCS
│       └── typing.py                       # Pydantic models for feedback
│
├── tests/                                  # Test suite
│   ├── unit/test_dummy.py                  # Placeholder unit tests
│   ├── integration/test_server_e2e.py      # E2E server tests
│   └── eval/
│       ├── eval_config.yaml                # Evaluation metrics config
│       └── datasets/                       # Custom eval datasets
│
├── docs/                                   # Documentation
│   ├── architecture.md                     # Architecture diagrams
│   ├── codebase-summary.md                 # This file
│   ├── code-standards.md                   # Development standards
│   ├── project-overview-pdr.md             # Product requirements
│   ├── system-architecture.md              # Technical design
│   ├── project-roadmap.md                  # Phases and progress
│   └── deployment-guide.md                 # Deployment instructions
│
├── Dockerfile                              # Docker image definition
├── pyproject.toml                          # Python project config (uv/hatch)
├── agents-cli-manifest.yaml                # ADK project manifest
├── CLAUDE.md                               # Claude Code guidance
├── AGENTS.md                               # Coding agent guidance
├── GEMINI.md                               # Gemini guidance
├── README.md                               # Quick start
└── .agents-cli-spec.md                     # ADK specification
```

## Module Responsibilities

### `app/agent.py` (816 LOC)

**Purpose:** Defines the complete multi-agent pipeline for log analysis.

**Key Components:**

1. **Structured Models (Pydantic):**
   - `LogEntry` — Single log entry with timestamp, severity, message, resource
   - `ErrorGroup` — Grouped errors with pattern, count, severity, affected resources
   - `LogAnalysisResult` — Complete analysis with error groups and summary
   - `InvestigationReport` — Final markdown report with findings and recommendations

2. **Tools (FunctionTool wrappers):**
   - `verify_gcloud_auth()` — Checks gcloud CLI installation and authentication
   - `fetch_gcp_logs()` — Runs `gcloud logging read` with filters, saves JSON
   - `analyze_log_file()` — Parses logs, groups errors by first 100 chars of message
   - `save_report()` — Writes markdown report to `plans/reports/`

3. **Agents:**
   - `PreflightChecker` — Verifies gcloud auth before pipeline runs
   - `param_gatherer` — Extracts environment, severity, freshness from user request
   - `log_fetcher` — Fetches logs from GCP Cloud Logging
   - `log_analyzer` — Groups errors, identifies patterns (with BuiltInPlanner enabled)
   - `report_composer` — Generates markdown investigation report
   - `report_saver` — Saves report to disk with metadata
   - `log_analyst_coordinator` (root) — Understands user request, delegates to pipeline

4. **Callbacks:**
   - `collect_errors_callback` — Deduplicates errors across passes into `all_errors`
   - `build_report_callback` — Computes severity level, adds markdown header

### `app/config.py`

**Purpose:** Centralized configuration for environments and model settings.

**Key Data:**
- `env_map` — Maps environment names (dev-vn, dev, test, performance, prod) to GCP projects, clusters, regions
- `worker_model` — Default model for agent reasoning (gemini-2.0-flash)
- `default_severity`, `default_freshness`, `default_limit` — Analysis parameters
- Helper methods: `get_project()`, `get_cluster()`, `get_region()`

### `app/fast_api_app.py`

**Purpose:** FastAPI server wrapper with telemetry and feedback endpoints.

**Features:**
- Wraps ADK's `get_fast_api_app(app)` for HTTP interface
- `POST /run` with streaming (SSE) — Analysis requests
- `POST /feedback` — User feedback collection
- OpenTelemetry instrumentation (logs to GCS if `LOGS_BUCKET_NAME` set)
- CORS configuration from `ALLOW_ORIGINS` env var

### `app/app_utils/telemetry.py`

**Purpose:** OpenTelemetry setup for GCS telemetry upload.

**Exports:**
- `setup_telemetry()` — Configures OTel with GCS exporter, message content filtering

### `app/app_utils/typing.py`

**Purpose:** Pydantic models for API contracts.

**Models:**
- `Feedback` — User feedback structure for logging

## Data Flow

```
User Request
    ↓
[log_analyst_coordinator] — understands intent
    ↓
[param_gatherer] → analysis_params
    ↓
[log_fetcher] → fetch_result (JSON)
    ↓
[log_analyzer] → log_analysis (structured) → collect_errors_callback aggregates
    ↓
[report_composer] → investigation_report → build_report_callback finalizes
    ↓
[report_saver] → saves to plans/reports/log-analysis-{env}-{ts}.md
    ↓
Response to user
```

## Session State Keys

Agents communicate exclusively via session state (`output_key` in ADK):

| Key | Producer | Consumer | Type |
|-----|----------|----------|------|
| `analysis_params` | param_gatherer | log_fetcher, report_composer | Dict[str, Any] |
| `fetch_result` | log_fetcher | log_analyzer, report_composer | Dict[str, str] |
| `log_analysis` | log_analyzer | report_composer, collect_errors_callback | LogAnalysisResult |
| `all_errors` | collect_errors_callback | — | List[ErrorGroup] |
| `investigation_report` | report_composer | build_report_callback | str (markdown) |
| `final_report` | build_report_callback | report_saver | str (with header) |
| `save_result` | report_saver | — | Dict[str, str] |

## ADK Patterns Used

1. **`output_key`** — Sole inter-agent communication mechanism; no direct agent calls
2. **`BuiltInPlanner(ThinkingConfig)`** — Extended reasoning enabled only on `log_analyzer`
3. **`include_contents="none"`** — Prevents `report_composer` and `report_saver` from seeing chat history
4. **`after_agent_callback`** — Event hook for error deduplication and report finalization
5. **`_EvalSequentialAgent`** — SequentialAgent subclass with `instruction` and `tools` fields for eval harness
6. **`PreflightChecker(BaseAgent)`** — Custom agent for auth verification before pipeline

## Configuration

**Environment Variables:**
- `GOOGLE_GENAI_USE_VERTEXAI` — Set to `TRUE` (required)
- `GOOGLE_CLOUD_PROJECT` — GCP project for Vertex AI (required)
- `GOOGLE_CLOUD_LOCATION` — Vertex AI region, e.g. `global` (required)
- `LOGS_BUCKET_NAME` — GCS bucket for telemetry (optional)
- `ALLOW_ORIGINS` — CORS origins (optional)
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` — Set to `NO_CONTENT` to enable telemetry

**GCP Environment Map:**
- dev-vn: klara-nonprod / klara-dev-vn / asia-southeast1-a
- dev: klara-nonprod / klara-nonprod / europe-west6-a
- test: klara-nonprod / klara-nonprod / europe-west6-a
- performance: klara-performance / klara-performance / europe-west6-a
- prod: klara-prod / klara-prod / europe-west6-a

## Severity Scoring

Report severity is calculated from error count:
- `critical` → >50 errors
- `high` → >20 errors
- `medium` → >5 errors
- `low` → ≤5 errors

## Entry Points

1. **Local Testing:** `agents-cli playground`
2. **CLI Test:** `agents-cli run "analyze errors in dev-vn last 2 hours"`
3. **API Server:** `adk api_server --port 8000` or `uvicorn app.fast_api_app:app`
4. **FastAPI Direct:** `POST /run` with analysis request
5. **User Feedback:** `POST /feedback` with user ratings

## Key Files to Modify When...

| Task | File(s) |
|------|---------|
| Add new GCP environment | `app/config.py` (add to `env_map`) |
| Add new agent to pipeline | `app/agent.py` (define agent, add to `log_analysis_pipeline`) |
| Modify error grouping logic | `app/agent.py` → `analyze_log_file()` function |
| Change severity thresholds | `app/agent.py` → `build_report_callback()` |
| Add new tool | `app/agent.py` → define function, wrap with `FunctionTool()` |
| Modify report format | `app/agent.py` → `report_composer` agent prompt or callback |
| Change API endpoints | `app/fast_api_app.py` |

## Testing

- **Unit Tests:** `pytest tests/unit/`
- **Integration Tests:** `pytest tests/integration/` (starts FastAPI server)
- **Eval:** `agents-cli eval run` (uses datasets in `tests/eval/datasets/`)
- **All Tests:** `pytest`

## Build & Deployment

- **Build:** `uv sync` (install dependencies), `python -m pytest` (run tests)
- **Local Run:** `adk api_server --port 8000`
- **Docker:** `docker build -t log-analyzer .` (runs on port 8080)
- **Agent Runtime:** `agents-cli deploy` (managed GCP deployment)

## Dependencies Summary

**Core:**
- google-adk >=1.15.0 — Agent framework
- google-cloud-logging >=3.12.0 — GCP logging client
- opentelemetry-instrumentation-google-genai — Telemetry
- gcsfs >=2024.11.0 — GCS integration

**Dev:**
- pytest, pytest-asyncio — Testing
- ruff, ty, codespell — Linting

**Eval (Optional):**
- google-adk[eval] — Evaluation harness
- google-cloud-aiplatform[evaluation] — Scoring

## Code Quality Standards

- **Python 3.11+** minimum
- **ruff** for linting: line-length=88, selects E/F/W/I/C/B/UP/RUF
- **ty** for type checking (astral rust-based checker)
- **codespell** for spell checking
- No persistent session storage (in-memory only)
- Async-first design with asyncio

## Phase Status

**Phase 1 (Complete):**
- Core multi-agent pipeline
- GCP log fetching and analysis
- Markdown report generation

**Phase 2 (In Progress):**
- Real unit tests (test_dummy.py is placeholder)
- Eval datasets and metrics
- Error deduplication improvements

**Phase 3 (Planned):**
- ML-based error clustering
- Multi-project analysis
- Slack/PagerDuty integration
- Persistent session storage
- Agent Runtime deployment
