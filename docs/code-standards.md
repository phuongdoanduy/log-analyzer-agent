# Log Analyzer Agent — Code Standards

## Language & Package Management

### Python Version
- **Minimum:** Python 3.11
- **Target:** Python 3.11 to 3.13
- **Policy:** Use modern Python features (match expressions, type hints, async/await)

### Package Manager
- **Tool:** uv (Astral's fast Python package manager)
- **Lock File:** uv.lock (committed to git)
- **Install:** `uv sync` (all dependencies including dev)
- **Add Dependency:** `uv add package_name`
- **Build Backend:** hatchling (via pyproject.toml)

### Dependency Constraints
- Keep dependencies minimal; prefer stdlib where possible
- Pin major versions in pyproject.toml (e.g., `>=1.15.0,<2.0.0`)
- Audit security advisories weekly (use `uv audit`)
- No pip; always use uv

## Linting & Code Quality

### Linter: ruff
- **Config:** `pyproject.toml` [tool.ruff]
- **Line Length:** 88 characters
- **Selected Rules:** E (pycodestyle), F (pyflakes), W (warnings), I (isort), C (comprehensions), B (bugbear), UP (pyupgrade), RUF (ruff-specific)
- **Ignored:** E501 (line too long), C901 (too complex), B006 (mutable default)

**Run:** `agents-cli lint` or `uv run ruff check .`

**Common Fixes:**
```bash
# Auto-fix import sorting and simple issues
uv run ruff check --fix .

# Check only
uv run ruff check .
```

### Type Checker: ty
- **Tool:** Astral's Rust-based type checker (same team as ruff/uv)
- **Config:** `pyproject.toml` [tool.ty]
- **Strategy:** Ignore common issues with third-party library stubs (ty is conservative)

**Run:** `agents-cli lint` or `uv run ty check .`

**Note:** ty errors are informational; ruff violations must be fixed.

### Spell Checker: codespell
- **Config:** `pyproject.toml` [tool.codespell]
- **Ignored Words:** "rouge" (color, not rogue)

**Run:** `agents-cli lint` or `uv run codespell .`

### Pre-commit Workflow
```bash
# Before committing, run linters
agents-cli lint

# Fix auto-fixable issues
uv run ruff check --fix .

# Run tests
pytest

# Commit if all pass
git add .
git commit -m "feat: your change"
```

## Code Organization

### File Naming
- **Python files:** kebab-case.py (e.g., `fast_api_app.py`, `app_utils.py`)
- **Directories:** kebab-case or context-based (e.g., `app_utils/`, `tests/`)
- **Self-documenting:** Filenames should describe purpose without reading contents

### Module Structure
```
app/
├── agent.py              # All agents, tools, models, callbacks
├── config.py             # Configuration and env map
├── fast_api_app.py       # FastAPI server wrapper
└── app_utils/
    ├── telemetry.py      # OTel setup
    └── typing.py         # Pydantic models for API contracts
```

### Import Organization
ruff (isort) enforces this order:
1. Future imports (`from __future__ import ...`)
2. Standard library (os, sys, json, etc.)
3. Third-party (google.adk, pydantic, fastapi, etc.)
4. First-party (app, frontend, etc.)

**Example:**
```python
from __future__ import annotations

import json
from typing import Any

from google.adk.agents import LlmAgent
from pydantic import BaseModel

from app.config import config
```

## Type Hints

### Policy
- **Mandatory:** Function parameters and return types on all public APIs
- **Optional:** Local variables (infer when obvious)
- **Collections:** Always use generic types (List[str], Dict[str, int], not list, dict)

### Examples
```python
def analyze_log_file(log_file: str) -> LogAnalysisResult:
    """Analyze logs and return structured result."""
    errors: dict[str, int] = {}
    entries: list[LogEntry] = []
    return LogAnalysisResult(...)

async def fetch_logs(
    project: str,
    severity: str,
    freshness: str,
    limit: int = 500,
) -> dict[str, Any]:
    """Fetch logs from GCP."""
    ...
```

### Union Types
```python
# Python 3.10+ style (preferred)
def process(data: str | None) -> int | None:
    ...

# Avoid: from typing import Union
def process(data: Union[str, None]) -> Union[int, None]:
    ...
```

## Code Comments & Docstrings

### Docstring Format
Use Google-style docstrings (ruff enforces D417 compliance):

```python
def verify_gcloud_auth() -> str:
    """Verify gcloud CLI is installed and authenticated.

    Checks for gcloud binary in PATH, validates active account,
    and retrieves current project ID.

    Returns:
        JSON string with auth status, account, and project.

    Raises:
        RuntimeError: If gcloud is not installed or not authenticated.
    """
```

### Inline Comments
- Explain "why" not "what" (code shows what)
- One comment per concept
- No stale comments; update when code changes

```python
# ✅ Good: explains domain logic
# Deduplicates errors using first 100 chars of message as key
errors: dict[str, int] = {}
for entry in logs:
    key = entry.message[:100]
    errors[key] = errors.get(key, 0) + 1

# ❌ Bad: obvious from code
# Loop through logs
for entry in logs:
    ...
```

### Section Comments
Use separator comments for major sections in large files:

```python
# ═══════════════════════════════════════════════════════════════
# Structured Output Models
# ═══════════════════════════════════════════════════════════════


class LogEntry(BaseModel):
    ...
```

## Testing

### Test Structure
```
tests/
├── unit/
│   ├── test_dummy.py                    # Placeholder (will be replaced)
│   └── test_config.py                   # Real unit tests (TBD)
├── integration/
│   └── test_server_e2e.py               # E2E: starts FastAPI server
└── eval/
    ├── eval_config.yaml                 # Custom metrics
    └── datasets/                        # Eval datasets
```

### Unit Tests
- **Framework:** pytest
- **Async:** pytest-asyncio (fixture_loop_scope = "function")
- **Coverage:** Aim for >80% on critical paths

**Example:**
```python
import pytest
from app.config import config


def test_get_project_valid_env():
    """Test config returns correct GCP project."""
    project = config.get_project("dev-vn")
    assert project == "klara-nonprod"


def test_get_project_invalid_env():
    """Test config raises on unknown environment."""
    with pytest.raises(ValueError, match="Unknown environment"):
        config.get_project("invalid-env")


@pytest.mark.asyncio
async def test_fetch_logs_integration(monkeypatch):
    """Test log fetching with mocked gcloud."""
    # Use monkeypatch to mock subprocess.run
    ...
```

### Integration Tests
- **Start Server:** Use `pytest-asyncio` with test fixtures
- **HTTP Client:** Use httpx or requests
- **Cleanup:** Fixtures handle teardown

See `tests/integration/test_server_e2e.py` for patterns.

### Eval Tests
- **Config:** `tests/eval/eval_config.yaml` defines metrics
- **Datasets:** Add .jsonl or .json files to `tests/eval/datasets/`
- **Run:** `agents-cli eval run` (generates → grades → compares)

### Running Tests
```bash
# All tests
pytest

# Unit only
pytest tests/unit/

# Integration only
pytest tests/integration/ -v

# Specific test
pytest tests/unit/test_config.py::test_get_project_valid_env -v

# With coverage
pytest --cov=app --cov-report=html
```

## ADK Patterns & Conventions

### 1. Agent Definition
All agents inherit from ADK base classes (LlmAgent, SequentialAgent, BaseAgent):

```python
from google.adk.agents import LlmAgent, SequentialAgent

# Coordinator agent (user-facing)
coordinator = LlmAgent(
    id="log_analyst_coordinator",
    model="gemini-2.0-flash",
    system_prompt="You are a log analysis coordinator...",
)

# Pipeline agent (orchestrator)
pipeline = SequentialAgent(
    id="log_analysis_pipeline",
    agents=[
        param_gatherer,
        log_fetcher,
        log_analyzer,
        report_composer,
        report_saver,
    ],
)
```

### 2. Output Keys (Session State)
Agents communicate via `output_key` (immutable state keys):

```python
log_fetcher = LlmAgent(
    id="log_fetcher",
    ...,
    output_key="fetch_result",  # Stores result in session["fetch_result"]
)
```

**Read from state:**
```python
# Inside agent, access previous agent's output via context
context.session.state.get("fetch_result")
```

### 3. Tools (FunctionTool)
Wrap functions with FunctionTool for agent access:

```python
from google.adk.tools import FunctionTool

def fetch_gcp_logs(project: str, severity: str, ...) -> dict[str, str]:
    """Fetch logs from GCP."""
    ...

log_fetcher = LlmAgent(
    id="log_fetcher",
    tools=[
        FunctionTool(fetch_gcp_logs),
    ],
)
```

### 4. Callbacks (After-Agent Hooks)
Use `after_agent_callback` for post-processing:

```python
def collect_errors_callback(context: CallbackContext) -> EventActions:
    """Aggregate errors across passes."""
    log_analysis = context.session.state.get("log_analysis")
    if log_analysis:
        # Deduplicate and store in session["all_errors"]
        ...
    return EventActions()  # Continue pipeline

pipeline = SequentialAgent(
    id="log_analysis_pipeline",
    agents=[...],
    after_agent_callback=collect_errors_callback,
)
```

### 5. BuiltInPlanner (Extended Thinking)
Enable only on agents that need deep reasoning:

```python
from google.adk.planners import BuiltInPlanner

log_analyzer = LlmAgent(
    id="log_analyzer",
    ...,
    planner=BuiltInPlanner(
        model="gemini-2.0-flash",
        thinking_config=ThinkingConfig(budget_tokens=5000),
    ),
)
```

### 6. Preflight Checks (Custom BaseAgent)
For validation before pipeline:

```python
from google.adk.agents import BaseAgent
from google.adk.events import EventActions

class PreflightChecker(BaseAgent):
    """Custom agent that runs synchronous checks."""

    async def call(self, context: InvocationContext) -> EventActions:
        """Verify gcloud auth."""
        try:
            verify_gcloud_auth()
            return EventActions()  # OK, continue
        except Exception as e:
            return EventActions(escalate=True, error=str(e))

preflight = PreflightChecker(id="preflight_checker")
```

### 7. include_contents="none"
Prevent agent from seeing chat history; read from state only:

```python
report_composer = LlmAgent(
    id="report_composer",
    ...,
    include_contents="none",  # Don't include previous messages
)
```

### 8. Pydantic Models for Structure
Use structured output models for data contracts:

```python
from pydantic import BaseModel, Field

class ErrorGroup(BaseModel):
    """A group of similar errors."""
    group_id: str = Field(description="Unique ID")
    error_pattern: str = Field(description="Message pattern")
    count: int = Field(description="Occurrences")
    ...

# Use in agent instructions for structured output
```

## Adding a New Agent to Pipeline

**Steps:**

1. **Define the agent** in `app/agent.py`:
   ```python
   new_agent = LlmAgent(
       id="new_step",
       model=config.worker_model,
       system_prompt="You are...",
       tools=[FunctionTool(some_tool)],
       output_key="new_step_output",
   )
   ```

2. **Add to SequentialAgent:**
   ```python
   pipeline = SequentialAgent(
       id="log_analysis_pipeline",
       agents=[
           param_gatherer,
           log_fetcher,
           log_analyzer,
           new_agent,  # ← Add here
           report_composer,
           report_saver,
       ],
   )
   ```

3. **Update session state keys** in docstring/README
4. **Test** with `agents-cli run "..."`

## Adding a New GCP Environment

**Steps:**

1. **Add to `config.py`:**
   ```python
   "new-env": {
       "project": "new-project-id",
       "cluster": "new-cluster",
       "region": "region-zone",
       "namespace": "new-env",
   },
   ```

2. **Update README** with new env in table
3. **Test:** `agents-cli run "analyze errors in new-env last 1h"`

## Adding a New Tool

**Steps:**

1. **Define function** in `app/agent.py`:
   ```python
   def new_tool(param1: str, param2: int) -> dict[str, str]:
       """Docstring with description of what tool does."""
       ...
       return {"result": "..."}
   ```

2. **Wrap with FunctionTool:**
   ```python
   new_agent = LlmAgent(
       id="new_agent",
       tools=[
           FunctionTool(new_tool),
       ],
   )
   ```

3. **Test** with agent

## Error Handling

### Policy
- **Prefer explicit exceptions** over silent failures
- **Provide context** in error messages (actual value, expected value)
- **Use try-catch** at agent boundaries; let tools raise

### Example
```python
def get_project(env: str) -> str:
    """Get GCP project for environment."""
    env_config = config.env_map.get(env.lower())
    if not env_config:
        raise ValueError(
            f"Unknown environment: {env}. "
            f"Valid options: {', '.join(config.env_map.keys())}"
        )
    return env_config["project"]
```

## Async/Await

### Policy
- Use async for I/O-bound operations (API calls, file I/O)
- Avoid blocking calls in async context
- Use `asyncio` for concurrency

### Example
```python
async def fetch_logs_async(project: str) -> dict[str, Any]:
    """Async wrapper for gcloud call."""
    # Use asyncio.to_thread for blocking subprocess
    result = await asyncio.to_thread(
        subprocess.run,
        ["gcloud", "logging", "read", ...],
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)
```

## FastAPI Patterns

### Endpoint Definition
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class AnalysisRequest(BaseModel):
    environment: str
    severity: str = "ERROR"

@app.post("/run")
async def run_analysis(request: AnalysisRequest):
    """Run analysis request."""
    # Delegate to agent via FastAPI app wrapper
    ...
```

### CORS Configuration
```python
# Set via environment
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "").split(",")
if ALLOW_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOW_ORIGINS,
        ...
    )
```

## Security Standards

### Credential Management
- ✅ Use gcloud CLI for authentication
- ✅ Use environment variables for API keys
- ❌ Do not hardcode credentials
- ❌ Do not store secrets in .py files

### Data Handling
- Log user queries (may contain service names)
- Don't log full error messages (may contain PII)
- Optional: redact sensitive fields in reports

### API Security
- Vertex AI auth via Application Default Credentials (no API key)
- Use CORS allow-list (ALLOW_ORIGINS)
- Audit logs via Google Cloud Logging

## Documentation Standards

### README
- Quick start (5 min setup)
- Prerequisites
- Key commands
- Architecture overview
- License

### Code Comments
- Explain "why" decisions (e.g., why error grouping uses first 100 chars)
- Link to architecture.md for diagrams
- Update when code changes

### Architecture Docs
- System diagrams (ASCII, Mermaid)
- Data flow
- Agent responsibilities
- Session state keys

## Build & Release

### Pre-commit Checks
```bash
# All these must pass before commit
agents-cli lint          # ruff + ty + codespell
pytest tests/unit/       # unit tests

# Fix issues
uv run ruff check --fix .
pytest tests/unit/ -v
```

### Version Bumping
- Use SemVer: MAJOR.MINOR.PATCH
- Bump in `pyproject.toml` [project] version
- Create git tag: `git tag v0.1.0`

### Docker Build
```bash
docker build -t log-analyzer:0.1.0 .
docker run -e GOOGLE_GENAI_USE_VERTEXAI=TRUE -e GOOGLE_CLOUD_PROJECT=your-project log-analyzer:0.1.0
```

## Summary Checklist

Before submitting code:
- [ ] Type hints on all public functions
- [ ] Docstrings (Google style)
- [ ] ruff lint passes (`agents-cli lint`)
- [ ] ty check passes (or documented ignores)
- [ ] codespell passes
- [ ] Unit tests pass (`pytest tests/unit/`)
- [ ] No hardcoded credentials
- [ ] Comments explain "why" not "what"
- [ ] ADK patterns used correctly
