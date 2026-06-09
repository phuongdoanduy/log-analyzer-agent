# Log Analyzer Agent — System Architecture

## Architecture Overview

The log analyzer agent uses a **sequential 6-agent pipeline** pattern orchestrated by Google ADK. Each agent is independent, communicates via session state keys, and delegates to specialized tools.

```
User Request (natural language)
    ↓
[LlmAgent] log_analyst_coordinator
    ├─ Understands intent
    ├─ Validates parameters
    └─ Delegates to pipeline
         ↓
[SequentialAgent] log_analysis_pipeline
    ├─ [Agent 0] preflight_checker → output_key: preflight_result
    ├─ [Agent 1] param_gatherer → output_key: analysis_params
    ├─ [Agent 2] log_fetcher → output_key: fetch_result
    ├─ [Agent 3] log_analyzer → output_key: log_analysis
    ├─ [Agent 4] report_composer → output_key: investigation_report
    └─ [Agent 5] report_saver → output_key: save_result
         ↓
[FastAPI] HTTP Server
    └─ Streaming response to client
```

For detailed ASCII diagrams, see `docs/architecture.md`.

## Agent Responsibilities

### 1. PreflightChecker (BaseAgent)
**When:** Before pipeline starts
**Responsibility:** Verify gcloud CLI is installed and authenticated
**Tool:** `verify_gcloud_auth()`
**Action:** Escalates if auth fails; otherwise continues to coordinator

**Design Rationale:**
- Fail fast before expensive operations
- Don't consume token budget on impossible analyses
- Clear error message to user

### 2. log_analyst_coordinator (LlmAgent)
**When:** Entry point for user request
**Responsibility:** 
- Parse natural language request ("analyze errors in dev-vn last 2 hours")
- Extract environment, severity threshold, time window
- Invoke analysis pipeline
- Present findings to user in conversational style

**Communication:** Delegates to pipeline, reads final_report from session
**Tokens:** Standard LLM reasoning

**Design Rationale:**
- Coordinator pattern: single user-facing interface
- Flexible input parsing: handles varied user phrasing
- Conversational output: explains findings to human

### 3. param_gatherer (LlmAgent)
**When:** First step in pipeline
**Responsibility:**
- Extract analysis parameters from coordinator's request
- Resolve environment name → GCP project ID (via config.py)
- Validate severity threshold (ERROR, WARNING, etc.)
- Determine time freshness (1h, 6h, 24h, 7d)
- Set log limit (default 500, configurable)

**Output:** `analysis_params` (dict)
```python
{
    "environment": "dev-vn",
    "project": "klara-nonprod",
    "severity": "ERROR",
    "freshness": "2h",
    "limit": 500,
}
```

**Tool:** None (pure reasoning)

**Design Rationale:**
- Single responsibility: parameter normalization
- Centralized environment resolution: uses config.py
- Fails gracefully on invalid environment

### 4. log_fetcher (LlmAgent)
**When:** After param_gatherer
**Responsibility:**
- Run `gcloud logging read` with filters
- Parse CLI response
- Save raw logs to JSON file
- Handle errors (API rate limits, network, auth) with structured error summary

**Input:** `analysis_params`
**Output:** `fetch_result` (dict)
**Success case:**
```python
{
    "status": "success",
    "log_file": "/tmp/gcp_logs.json",
    "logs_fetched": 487,
    "time_window": "2024-01-15T10:00 to 2024-01-15T12:00",
}
```
**Error case:** Starts with `FETCH_STATUS: ERROR` followed by 6-field structured summary:
- Environment requested
- GCP project targeted
- Error type (PERMISSION_DENIED | AUTH_EXPIRED | PROJECT_NOT_FOUND | TIMEOUT | UNKNOWN)
- Error detail (raw error message)
- Likely cause (plain English explanation)
- Recommended next steps (actionable steps)

**Tool:** `fetch_gcp_logs(project, severity, freshness, service_filter, limit, output_file, env)` — note env parameter for GKE cluster-scoped filtering

**Design Rationale:**
- Encapsulates gcloud CLI complexity
- Handles subprocess management
- Persists logs to disk for debugging/audit
- Structured error output enables downstream agents to recover gracefully

### 5. log_analyzer (LlmAgent + BuiltInPlanner)
**When:** After log_fetcher, with extended thinking enabled
**Responsibility:**
- Parse JSON log file
- Group errors by message pattern (first 100 chars)
- Calculate frequency, severity, first/last seen
- Identify affected resources
- Generate potential root causes (grounded in pattern evidence)

**GROUNDING RULE:** Every potential_cause must cite the exact pattern text and occurrence count from tool output. If evidence is insufficient, write "cause unknown — needs investigation" instead of inventing a cause.

**Input:** `fetch_result` (log file path)
**Output:** `log_analysis` (LogAnalysisResult)
```python
{
    "env": "dev-vn",
    "project": "klara-nonprod",
    "time_range": "2024-01-15T10:00 to 2024-01-15T12:00",
    "total_logs_fetched": 487,
    "total_errors": 124,
    "error_groups": [
        {
            "group_id": "g1",
            "error_pattern": "connection timeout to database",
            "count": 45,
            "severity": "ERROR",
            "first_seen": "2024-01-15T10:05:32Z",
            "last_seen": "2024-01-15T11:58:12Z",
            "affected_resources": ["api-pod-1", "api-pod-2"],
            "potential_cause": "Database replica lag or connectivity issue",
        },
        ...
    ],
}
```

**Tool:** `analyze_log_file(log_file: str) -> dict`

**Planner:** BuiltInPlanner(budget_tokens=5000)
- Enables extended reasoning for pattern detection
- Helps identify subtle correlations

**Callback:** `collect_errors_callback` deduplicates errors into `all_errors` key

**Design Rationale:**
- Extended thinking for complex pattern analysis
- Grouping by message prefix: simple, fast, tunable
- Callback aggregates errors across multiple passes
- Structured output for downstream agents

### 6. report_composer (LlmAgent)
**When:** After log_analyzer
**Responsibility:**
- Consume analysis_params, fetch_result, log_analysis
- Generate markdown investigation report
- Structure: executive summary, findings, recommendations
- Do NOT see chat history (include_contents="none")
- Handle fetch failures gracefully

**FETCH FAILURE HANDLING:**
If `fetch_result` contains "FETCH_STATUS: ERROR", generate 3-section "Analysis Incomplete" report only:
1. Executive Summary — state why analysis could not be completed
2. Error Details — environment, GCP project, error type, error detail, root cause
3. Recommended Next Steps — actionable steps for the user
Skip remaining sections. Still pass partial report to report_saver.

**COMPLETENESS & ANTI-HALLUCINATION RULES:**
- All 6 sections must always appear in full reports (skip partial for fetch failures)
- Every finding in sections 3 and 5 must trace to data in log_analysis
- Do NOT infer services, causes, or patterns beyond log_analysis
- Use severity-neutral language: "patterns/issues" not "errors" when severity is WARNING/INFO/DEBUG

**Input:** 
- `analysis_params` (environment, severity, etc.)
- `fetch_result` (may contain error details)
- `log_analysis` (structured analysis result)

**Output:** `investigation_report` (markdown string)
```markdown
# Log Analysis Report — dev-vn
Generated: 2024-01-15T12:30:00Z

## Executive Summary
Detected 124 errors over 2-hour period. Primary issue: database connection timeouts (45 occurrences). Secondary issues: authentication failures (23), missing resources (15).

## Log Summary
Total entries: 487
Severity breakdown:
- ERROR: 124
- WARNING: 89
- DEBUG: 274

## Detailed Findings
1. **Connection Timeout to Database** (45 errors)
   - Pattern: [first 100 chars from analysis]
   - Frequency: 45 occurrences
   - Affected Services: api-pod-1, api-pod-2, worker-pod-3
   - Potential Cause: Based on 45 occurrences of pattern '...'
   - Sample messages: [3 samples]

...

## Affected Services
- api-pod-1: 67 entries
- api-pod-2: 54 entries
- worker-pod-3: 31 entries

## Recommendations
[Evidence-grounded recommendations or "No actionable recommendations — log volume is below threshold"]

## Raw Data Reference
Log file: /tmp/gcp_logs.json
Time range: [from analysis_params]
Environment: [env from analysis_params]
```

**Tool:** None (pure reasoning)

**Design Rationale:**
- Markdown format: version-control friendly
- include_contents="none": prevents token waste on chat history
- Conversational tone: helps on-call engineers understand quickly
- Fetch failure handling: reports incomplete analysis instead of guessing
- All 6 sections always present: completeness for downstream parsing

### 7. report_saver (LlmAgent)
**When:** After report_composer
**Responsibility:**
- Receive composed report
- Add metadata header (environment, timestamp, severity)
- Save to `plans/reports/log-analysis-{env}-{ts}.md`
- Return file path

**Input:** `final_report` (markdown with header, from build_report_callback)

**Output:** `save_result` (dict)
```python
{
    "status": "success",
    "report_path": "plans/reports/log-analysis-dev-vn-20240115-123000.md",
}
```

**Tool:** `save_report(report_content, env, output_dir)`

**Design Rationale:**
- Persistent artifact: reports can be archived, audited
- Git-friendly: can commit reports to incidents repo
- Metadata: timestamp and env in filename for sorting

### 8. build_report_callback (After-Agent Callback)
**When:** After report_composer completes
**Responsibility:**
- Read `investigation_report` from session
- Compute severity level from error count:
  - critical: >50 errors
  - high: >20 errors
  - medium: >5 errors
  - low: ≤5 errors
- Add markdown header with metadata
- Store in `final_report` state key

**Action:** EventActions() — continue to report_saver

**Design Rationale:**
- Separation: severity logic separate from report composition
- Reusable: callback can be tested independently
- Pipeline extensibility: callbacks between agents

## Session State (Communication Bus — 8 Keys Total)

Agents **do not call each other directly**. They communicate via session state keys:

| Key | Set by | Type | Size | Lifecycle |
|-----|--------|------|------|-----------|
| `preflight_result` | preflight_checker | dict | <1 KB | terminal output to user (if auth fails) |
| `analysis_params` | param_gatherer | dict | <1 KB | read by log_fetcher, report_composer |
| `fetch_result` | log_fetcher | dict | <1 KB | read by log_analyzer, report_composer |
| `log_analysis` | log_analyzer | LogAnalysisResult | varies | read by report_composer, build_report_callback |
| `all_errors` | collect_errors_callback | list[ErrorGroup] | varies | aggregate (not read by others) |
| `investigation_report` | report_composer | str (markdown) | 10-50 KB | read by build_report_callback |
| `final_report` | build_report_callback | str (markdown + header) | 10-50 KB | read by report_saver |
| `save_result` | report_saver | dict | <1 KB | terminal output to user |

**Design Rationale:**
- ADK native pattern: output_key + session state
- Decoupling: agents don't import each other
- Visibility: state keys visible in session logs for debugging
- Atomicity: each output is immutable once set

## Tool Layer Design

### Tool Pattern
All tools follow this pattern:
1. Accept parameters (from agent reasoning or hardcoded)
2. Execute operation (subprocess, API call, file I/O)
3. Return structured result or raise exception
4. Never call another tool (composability via agents)

### Tool Examples

**verify_gcloud_auth()** → str
- No parameters
- Returns JSON with auth status
- Raises RuntimeError if not authenticated

**fetch_gcp_logs(project, severity, freshness, service_filter, limit, output_file)** → dict
- Parameters: GCP project, log severity filter, time window
- Executes: `gcloud logging read` subprocess with filters
- Returns: dict with status, file path, log count, time window
- Handles: subprocess errors, file I/O errors

**analyze_log_file(log_file)** → dict
- Parameters: path to JSON log file
- Executes: JSON parsing, error grouping by message pattern
- Returns: LogAnalysisResult with error groups
- Handles: JSON parsing errors, file not found

**save_report(report_content, env, output_dir)** → dict
- Parameters: markdown content, environment, output directory
- Executes: file write with timestamp filename
- Returns: dict with status, file path
- Handles: directory creation, file write errors

### Tool Design Principles
- **Single responsibility:** One operation per tool
- **Pure-ish:** Minimize side effects (except I/O which is intentional)
- **Testable:** Mock subprocess/file I/O in unit tests
- **Debuggable:** Return detailed result dicts, not bare values

## Callback Patterns

### Callback 1: collect_errors_callback
**When:** After log_analyzer executes
**Input:** CallbackContext (session, messages, etc.)
**Action:** Aggregate errors into cumulative database

```python
def collect_errors_callback(context: CallbackContext) -> EventActions:
    """Deduplicate and aggregate errors across passes."""
    log_analysis = context.session.state.get("log_analysis")
    if log_analysis:
        all_errors = context.session.state.get("all_errors", [])
        # Deduplicate by group_id, merge frequencies
        context.session.state.put("all_errors", deduplicated)
    return EventActions()  # Continue to next agent
```

**Design Rationale:**
- Runs after log_analyzer (only when needed)
- Doesn't block pipeline
- Enables multi-pass analysis (if we add it later)

### Callback 2: build_report_callback
**When:** After report_composer executes
**Input:** CallbackContext with investigation_report
**Action:** Compute severity, add header, store as final_report

```python
def build_report_callback(context: CallbackContext) -> EventActions:
    """Add metadata and compute severity level."""
    report = context.session.state.get("investigation_report")
    analysis = context.session.state.get("log_analysis")
    
    # Severity: based on error count
    severity = compute_severity(analysis.total_errors)
    
    # Header: metadata
    header = f"# Log Analysis — {severity.upper()}\n..."
    final = header + report
    
    context.session.state.put("final_report", final)
    return EventActions()  # Continue to report_saver
```

**Design Rationale:**
- Separates metadata logic from composition
- Reusable: can be tested independently
- Extensible: add metrics, flags, etc. without touching agents

## FastAPI Server

### HTTP Layer
```python
from google.adk.apps.app import get_fast_api_app

app = get_fast_api_app(log_agent, mode="sse")

# FastAPI wraps ADK agent in HTTP interface
# Provides: /run (POST), /feedback (POST), etc.
```

### Streaming Response
- **Endpoint:** `POST /run`
- **Input:** JSON with user prompt
- **Output:** Server-Sent Events (SSE) stream
  - Each agent completion triggers an event
  - Client receives real-time updates
  - Final response includes summary + report path

### Feedback Endpoint
- **Endpoint:** `POST /feedback`
- **Input:** Feedback Pydantic model
- **Action:** Log to Google Cloud Logging for analysis

### Telemetry
- **Setup:** `setup_telemetry()` in app_utils/telemetry.py
- **Exporter:** OpenTelemetry → GCS (if LOGS_BUCKET_NAME set)
- **Content Capture:** Configurable via OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT
  - "NO_CONTENT": log operation, hide sensitive data
  - Default: log full content

**Design Rationale:**
- ADK's FastAPI wrapper: minimal boilerplate
- Streaming: real-time feedback to user
- Telemetry: understand usage patterns, latency

## Error Handling Strategy

### Layer 1: Preflight (PreflightChecker)
- Check gcloud auth before starting
- Fail fast with clear message
- Escalate to user immediately

### Layer 2: Fetch Failure Detection (log_fetcher)
- Detects permission, auth, timeout errors from gcloud
- Outputs structured 6-field error summary with `FETCH_STATUS: ERROR` sentinel
- Downstream agents detect sentinel and generate "Analysis Incomplete" report instead of guessing

### Layer 3: Tool Exceptions
- Tools raise descriptive exceptions
- Agents see exception and can retry/escalate
- ADK captures and reports

### Layer 4: Agent Resilience
- Agents catch tool exceptions
- Agents can invoke fallback tools or escalate
- Report generation continues even if some logs fail

### Layer 5: Server Error Handling
- FastAPI catches unhandled exceptions
- Returns 500 with error summary
- OTel logs error for debugging

### Example: Missing Environment
```python
# param_gatherer LLM reasoning
agent: "I need to resolve 'invalid-env' to a GCP project"

# Tool execution
config.get_project("invalid-env")  # raises ValueError
# Error message: "Unknown environment: invalid-env. Valid options: dev-vn, dev, ..."

# Agent handling
agent: "The environment 'invalid-env' is not supported. 
         Please try: dev-vn, dev, test, performance, or prod"

# User sees clear, actionable error
```

## Data Models

### Input Models
- User request (natural language)
- Analysis parameters (environment, severity, freshness)

### Intermediate Models
- LogEntry (single log entry)
- ErrorGroup (grouped errors)
- LogAnalysisResult (analysis output)

### Output Models
- InvestigationReport (markdown + structured data)
- SaveResult (file path, status)

**Design Rationale:**
- Pydantic models: type safety, validation, serialization
- Clear contracts: each agent knows what to expect
- Composable: models pass between agents via state

## Extensibility Points

### Add a New Agent
1. Define agent in app/agent.py
2. Add to log_analysis_pipeline.agents list
3. Define output_key for state communication

### Add a New Tool
1. Define function in app/agent.py
2. Wrap with FunctionTool
3. Add to agent's tools list

### Add a New Environment
1. Add entry to config.env_map
2. Test with agents-cli run

### Add a New Callback
1. Define function matching CallbackContext signature
2. Add to agent or pipeline's after_agent_callback

### Change Error Grouping
1. Modify analyze_log_file() function
2. Adjust message pattern threshold (100 chars → other value)
3. Test with sample logs

### Change Severity Thresholds
1. Modify build_report_callback()
2. Adjust critical/high/medium/low ranges
3. Test with eval dataset

## Performance Characteristics

### Typical Request Flow
1. **Preflight check:** 100-200ms (gcloud availability)
2. **Coordinator parsing:** 500ms-1s (LLM reasoning)
3. **Param gathering:** 500ms (env resolution, normalization)
4. **Log fetching:** 2-10s (gcloud API call + JSON write)
5. **Log analysis:** 3-8s (JSON parsing + grouping, + extended thinking)
6. **Report composition:** 1-3s (LLM generation)
7. **Report save:** 100-200ms (file write)

**Total:** ~8-25 seconds for typical 500-log analysis

### Memory Profile
- Session state: <500 KB (parameters, log paths, analysis results)
- Temporary files: ~5-10 MB (raw logs JSON)
- Models in memory: <50 MB (agents, tools)

### Scalability
- In-memory sessions: supports concurrent requests (stateless per session)
- gcloud CLI: respects rate limits, includes retry logic
- Gemini API: token budget per request (watch latency under high load)

## Security Architecture

### Authentication & Authorization
- **GCP Auth:** gcloud CLI handles credentials (no hardcoded keys)
- **Gemini/Vertex AI:** Application Default Credentials via `gcloud auth login --update-adc` (no API key in code)
- **User Auth:** FastAPI could add OAuth/JWT (Phase 3)

### Data Flow Security
1. User request (may include service names)
2. Agent reasoning (logs to Google Cloud Logging)
3. Raw logs (stored in /tmp, not persisted after session)
4. Reports (stored in plans/reports/, version-controlled)
5. Feedback (logged to Google Cloud Logging)

### Sensitive Data Handling
- ✅ Log service names and error patterns
- ✅ Log investigation findings (non-PII)
- ❌ Do not log full stack traces or raw data
- ❌ Do not log user credentials or API keys

### Audit Trail
- ADK logs all agent calls and reasoning
- OTel telemetry (if enabled) goes to GCS
- Reports archived in git (commits with timestamps)
- Feedback logged to Cloud Logging (queryable)

## Deployment Architecture

### Local Development
```
User → agents-cli playground
     → FastAPI (8000)
     → ADK agents
     → gcloud CLI → GCP Logging API
```

### Docker Deployment
```
User → Cloud Run / Docker
     → FastAPI (8080)
     → ADK agents
     → gcloud CLI (with Application Default Credentials)
     → GCP Logging API
```

### Agent Runtime Deployment
```
User → Agent Runtime (managed by Google)
     → ADK FastAPI app
     → Agents
     → GCP services
```

See `docs/deployment-guide.md` for detailed setup.

## Diagram References

- **Architecture Diagram:** `docs/architecture.md` (ASCII, full pipeline)
- **Data Flow:** `docs/architecture.md` (state keys, agent communication)
- **Deployment Options:** `docs/architecture.md` (local, Docker, Agent Runtime)

## Summary

**Key Design Principles:**
1. Sequential pipeline: simple, debuggable, testable
2. Session state: decoupled, visible, auditable
3. Tool abstraction: reusable, mockable, composable
4. Callback hooks: extensible without modifying agents
5. Structured models: type-safe, contract-explicit
6. Error-first: fail fast, clear messages, detailed context
