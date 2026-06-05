# Copyright 2026 Optimus Team
# MIT License
#
# Log Analyzer Agent — GCP Log Analysis & Incident Investigation
# Architecture: Google ADK (Agent Development Kit)
# Pattern: Preflight → Gather Params → Fetch Logs → Analyze → Report

from __future__ import annotations

import datetime
import json
import logging
import subprocess
from collections.abc import AsyncGenerator
from typing import Literal

from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.apps.app import App
from google.adk.events import Event, EventActions
from google.adk.tools import FunctionTool
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from .config import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Structured Output Models
# ═══════════════════════════════════════════════════════════════


class LogEntry(BaseModel):
    """A single log entry from GCP Cloud Logging."""

    timestamp: str = Field(description="Log timestamp (ISO 8601)")
    severity: str = Field(description="Log severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    message: str = Field(description="Log message content")
    resource: str = Field(default="", description="GCP resource (container, pod, service)")
    labels: dict[str, str] = Field(default_factory=dict, description="Log labels")
    trace: str = Field(default="", description="Trace ID for correlation")
    insert_id: str = Field(default="", description="Unique log insert ID")


class ErrorGroup(BaseModel):
    """A group of similar errors found in logs."""

    group_id: str = Field(description="Unique group identifier")
    error_pattern: str = Field(description="Common error pattern/message")
    count: int = Field(description="Number of occurrences")
    severity: Literal["CRITICAL", "ERROR", "WARNING"] = Field(description="Highest severity in group")
    first_seen: str = Field(description="First occurrence timestamp")
    last_seen: str = Field(description="Last occurrence timestamp")
    affected_resources: list[str] = Field(default_factory=list, description="Affected services/containers")
    sample_messages: list[str] = Field(default_factory=list, description="Sample error messages (max 3)")
    potential_cause: str = Field(default="", description="Potential root cause analysis")


class LogAnalysisResult(BaseModel):
    """Complete log analysis output."""

    env: str = Field(description="GCP environment analyzed")
    project: str = Field(description="GCP project ID")
    time_range: str = Field(description="Time range analyzed")
    total_logs_fetched: int = Field(description="Total log entries fetched")
    total_errors: int = Field(description="Total error-level entries")
    total_warnings: int = Field(description="Total warning-level entries")
    error_groups: list[ErrorGroup] = Field(default_factory=list, description="Grouped errors")
    top_errors: list[str] = Field(default_factory=list, description="Top 5 error patterns")
    services_affected: list[str] = Field(default_factory=list, description="Affected services")
    summary: str = Field(description="Brief analysis summary")


class InvestigationReport(BaseModel):
    """Final investigation report."""

    title: str = Field(description="Report title")
    severity_level: str = Field(description="Overall severity: critical/high/medium/low")
    executive_summary: str = Field(description="2-3 sentence summary")
    findings: list[dict] = Field(default_factory=list, description="Detailed findings")
    recommendations: list[str] = Field(default_factory=list, description="Recommended actions")
    raw_log_path: str = Field(default="", description="Path to raw log file")
    report_path: str = Field(default="", description="Path to saved report")


# ═══════════════════════════════════════════════════════════════
# Tools — GCP Log Operations
# ═══════════════════════════════════════════════════════════════


def verify_gcloud_auth() -> str:
    """Verify gcloud CLI is installed and authenticated.

    Returns:
        JSON with auth status, active account, and project.
    """
    try:
        # Check gcloud installed
        result = subprocess.run(
            ["gcloud", "version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return json.dumps({
                "status": "error",
                "message": "gcloud CLI not installed or not in PATH",
            })

        # Check auth status
        result = subprocess.run(
            ["gcloud", "auth", "list", "--format=json"],
            capture_output=True, text=True, timeout=10,
        )
        accounts = json.loads(result.stdout) if result.returncode == 0 else []
        active = [a for a in accounts if a.get("status") == "ACTIVE"]

        # Check current project
        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True, text=True, timeout=10,
        )
        current_project = result.stdout.strip() if result.returncode == 0 else "none"

        return json.dumps({
            "status": "ok" if active else "not_authenticated",
            "active_account": active[0].get("account", "none") if active else "none",
            "current_project": current_project,
            "all_accounts": [a.get("account") for a in accounts],
        })
    except FileNotFoundError:
        return json.dumps({"status": "error", "message": "gcloud CLI not found"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def fetch_gcp_logs(
    project: str,
    severity: str = "ERROR",
    freshness: str = "1h",
    service_filter: str = "",
    limit: int = 500,
    output_file: str = "/tmp/gcp_logs.json",
    env: str = "",
) -> str:
    """Fetch logs from GCP Cloud Logging using gcloud CLI.

    Args:
        project: GCP project ID.
        severity: Minimum severity level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        freshness: Time window (e.g. '1h', '2h', '30m', '1d').
        service_filter: Optional service/container name filter.
        limit: Maximum number of log entries to fetch.
        output_file: Path to save fetched logs as JSON.
        env: Optional GCP environment name to target GKE container logs.

    Returns:
        JSON with fetch status, count, and output file path.
    """
    try:
        # Build gcloud logging read filter
        severity_filter = f'severity>={severity}' if severity != 'DEFAULT' else ''

        # Parse freshness to timestamp
        unit = freshness[-1]
        value = int(freshness[:-1])
        now = datetime.datetime.utcnow()
        if unit == 'h':
            start = now - datetime.timedelta(hours=value)
        elif unit == 'm':
            start = now - datetime.timedelta(minutes=value)
        elif unit == 'd':
            start = now - datetime.timedelta(days=value)
        else:
            start = now - datetime.timedelta(hours=1)

        timestamp_filter = f'timestamp>="{start.isoformat()}Z"'

        # Build filter string
        filters = [timestamp_filter]

        # Scope to GKE containers to avoid project-level permission issues
        filters.append('resource.type="k8s_container"')

        if env:
            env_config = config.env_map.get(env.lower())
            if env_config:
                cluster = env_config.get("cluster")
                location = env_config.get("region")
                namespace = env_config.get("namespace")
                if cluster:
                    filters.append(f'resource.labels.cluster_name="{cluster}"')
                if location:
                    filters.append(f'resource.labels.location="{location}"')
                if namespace:
                    filters.append(f'resource.labels.namespace_name="{namespace}"')

        if severity_filter:
            filters.append(severity_filter)
        if service_filter:
            filters.append(f'resource.labels.container_name="{service_filter}"')

        filter_str = " AND ".join(filters)

        # Run gcloud logging read
        cmd = [
            "gcloud", "logging", "read", filter_str,
            f"--project={project}",
            f"--limit={limit}",
            "--format=json",
            "--freshness=" + freshness,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=120,
        )

        if result.returncode != 0:
            return json.dumps({
                "status": "error",
                "message": result.stderr.strip(),
                "count": 0,
            })

        logs = json.loads(result.stdout) if result.stdout.strip() else []

        # Save to file
        with open(output_file, "w") as f:
            json.dump(logs, f, indent=2)

        return json.dumps({
            "status": "ok",
            "count": len(logs),
            "output_file": output_file,
            "project": project,
            "filter": filter_str,
            "time_range": f"{start.isoformat()}Z to now",
        })

    except subprocess.TimeoutExpired:
        return json.dumps({
            "status": "error",
            "message": "gcloud command timed out after 120s",
            "count": 0,
        })
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "message": f"Failed to parse gcloud output: {e}",
            "count": 0,
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
            "count": 0,
        })


def analyze_log_file(log_file: str = "/tmp/gcp_logs.json") -> str:
    """Analyze a fetched log file and produce structured analysis.

    Args:
        log_file: Path to the JSON log file from fetch_gcp_logs.

    Returns:
        JSON with analysis results: error groups, severity breakdown, top errors.
    """
    try:
        with open(log_file) as f:
            logs = json.load(f)

        if not logs:
            return json.dumps({
                "status": "empty",
                "message": "No logs found in the specified time range.",
                "total_logs": 0,
            })

        # Severity breakdown
        severity_counts = {}
        error_messages = []
        resources_seen = set()

        for entry in logs:
            sev = entry.get("severity", "DEFAULT")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            # Extract resource info
            resource = entry.get("resource", {})
            labels = resource.get("labels", {})
            container = labels.get("container_name", "")
            if container:
                resources_seen.add(container)

            # Collect error messages for grouping
            if sev in ("ERROR", "CRITICAL"):
                text = ""
                payload = entry.get("textPayload", "")
                json_payload = entry.get("jsonPayload", {})
                if payload:
                    text = payload
                elif json_payload:
                    text = json.dumps(json_payload)
                if text:
                    error_messages.append({
                        "message": text[:500],
                        "severity": sev,
                        "timestamp": entry.get("timestamp", ""),
                        "resource": container,
                    })

        # Simple error grouping by message prefix (first 100 chars)
        groups = {}
        for err in error_messages:
            # Group by first 100 chars of message
            key = err["message"][:100]
            if key not in groups:
                groups[key] = {
                    "pattern": key,
                    "count": 0,
                    "severity": err["severity"],
                    "first_seen": err["timestamp"],
                    "last_seen": err["timestamp"],
                    "resources": set(),
                    "samples": [],
                }
            groups[key]["count"] += 1
            groups[key]["last_seen"] = err["timestamp"]
            if err["resource"]:
                groups[key]["resources"].add(err["resource"])
            if len(groups[key]["samples"]) < 3:
                groups[key]["samples"].append(err["message"][:200])

        # Convert sets to lists for JSON
        error_groups = []
        for g in sorted(groups.values(), key=lambda x: x["count"], reverse=True):
            error_groups.append({
                "pattern": g["pattern"],
                "count": g["count"],
                "severity": g["severity"],
                "first_seen": g["first_seen"],
                "last_seen": g["last_seen"],
                "resources": list(g["resources"]),
                "samples": g["samples"],
            })

        return json.dumps({
            "status": "ok",
            "total_logs": len(logs),
            "severity_breakdown": severity_counts,
            "total_errors": severity_counts.get("ERROR", 0) + severity_counts.get("CRITICAL", 0),
            "total_warnings": severity_counts.get("WARNING", 0),
            "error_groups": error_groups[:20],  # Top 20 groups
            "top_errors": [g["pattern"] for g in error_groups[:5]],
            "services_affected": list(resources_seen),
        })

    except FileNotFoundError:
        return json.dumps({
            "status": "error",
            "message": f"Log file not found: {log_file}",
        })
    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "message": f"Invalid JSON in log file: {e}",
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e),
        })


def save_report(report_content: str, env: str, output_dir: str = "plans/reports") -> str:
    """Save the investigation report to a markdown file.

    Args:
        report_content: The markdown report content.
        env: Environment name (for filename).
        output_dir: Directory to save the report.

    Returns:
        JSON with the saved file path.
    """
    import os
    from pathlib import Path

    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        date_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"log-analysis-{env}-{date_str}.md"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w") as f:
            f.write(report_content)

        return json.dumps({
            "status": "ok",
            "filepath": filepath,
            "filename": filename,
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# Wrap as ADK FunctionTools
gcloud_auth_tool = FunctionTool(verify_gcloud_auth)
log_fetch_tool = FunctionTool(fetch_gcp_logs)
log_analyze_tool = FunctionTool(analyze_log_file)
report_save_tool = FunctionTool(save_report)


# ═══════════════════════════════════════════════════════════════
# MCP Integration — polaris-mcp-server
# ═══════════════════════════════════════════════════════════════

# MCP toolset for polaris-mcp-server (skill-based tools)
# The MCP server returns skill content (Markdown guides) that the agent
# reads and follows. This is the "Skill Driven" pattern.
#
# To use MCP tools, uncomment and configure:
#
# polaris_mcp = McpToolset(
#     server_params={
#         "command": "npx",
#         "args": ["-y", "@polaris/mcp-server"],
#         "env": {
#             "POLARIS_PORT": "3003",
#         },
#     },
#     tool_filter=[
#         "gcloud-setup",
#         "gcp-fetch-logs",
#         "log-analysis",
#         "root-cause-report",
#     ],
# )


# ═══════════════════════════════════════════════════════════════
# Callbacks — Side Effects
# ═══════════════════════════════════════════════════════════════


def init_coordinator_state(callback_context: CallbackContext) -> None:
    """Initialize state keys used in coordinator instruction template.

    Prevents 'Context variable not found' on the first turn before the
    pipeline has run and populated these keys.
    """
    state = callback_context.state
    for key in ("final_report", "investigation_report"):
        if key not in state:
            state[key] = ""


def collect_errors_callback(callback_context: CallbackContext) -> None:
    """Collects and deduplicates errors from log analysis results.

    Processes session state to build a cumulative error database
    with deduplication by error pattern.
    """
    analysis = callback_context.state.get("log_analysis", "")
    if not analysis:
        return

    try:
        data = json.loads(analysis) if isinstance(analysis, str) else analysis
        error_groups = data.get("error_groups", [])

        existing = callback_context.state.get("all_errors", [])
        seen_patterns = {e.get("pattern", "") for e in existing}

        for group in error_groups:
            pattern = group.get("pattern", "")
            if pattern and pattern not in seen_patterns:
                existing.append(group)
                seen_patterns.add(pattern)

        callback_context.state["all_errors"] = existing
    except (json.JSONDecodeError, TypeError):
        pass


def build_report_callback(callback_context: CallbackContext) -> genai_types.Content:
    """Post-processes the investigation report with summary statistics.

    Computes severity level, adds metadata header.
    """
    def clean_json_str(raw_str: str) -> str:
        raw_str = raw_str.strip()
        if raw_str.startswith("```"):
            lines = raw_str.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_str = "\n".join(lines).strip()
        return raw_str

    report = callback_context.state.get("investigation_report", "")
    analysis = callback_context.state.get("log_analysis", "")
    
    # Try to resolve environment
    env = callback_context.state.get("target_env", "")
    if not env:
        params_str = callback_context.state.get("analysis_params", "")
        if params_str:
            try:
                params_data = json.loads(clean_json_str(params_str))
                env = params_data.get("env", "unknown")
            except Exception:
                env = "unknown"
        else:
            env = "unknown"

    # Determine overall severity
    severity_level = "low"
    if analysis:
        try:
            cleaned_analysis = clean_json_str(analysis)
            data = json.loads(cleaned_analysis) if isinstance(cleaned_analysis, str) else cleaned_analysis
            total_errors = data.get("total_errors")
            if total_errors is None:
                # Sum ERROR and CRITICAL from breakdown
                breakdown = data.get("severity_breakdown", {})
                total_errors = sum(
                    count for level, count in breakdown.items()
                    if level.upper() in ("ERROR", "CRITICAL", "FATAL")
                )
            if total_errors > 50:
                severity_level = "critical"
            elif total_errors > 20:
                severity_level = "high"
            elif total_errors > 5:
                severity_level = "medium"
        except (json.JSONDecodeError, TypeError):
            pass

    # Add metadata header
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"""# Log Analysis Report — {env.upper()}

**Generated:** {date_str}
**Severity:** {severity_level.upper()}
**Environment:** {env}

---

"""
    final_report = header + report
    callback_context.state["final_report"] = final_report

    return genai_types.Content(parts=[genai_types.Part(text=final_report)])


# ═══════════════════════════════════════════════════════════════
# Eval-compatible wrappers
# ═══════════════════════════════════════════════════════════════


class _EvalSequentialAgent(SequentialAgent):
    instruction: str = ""
    tools: list = []


# ═══════════════════════════════════════════════════════════════
# Custom Agent for Preflight Check
# ═══════════════════════════════════════════════════════════════


class PreflightChecker(BaseAgent):
    """Checks gcloud authentication and environment readiness.

    In production (STRICT_PREFLIGHT=true) auth failure escalates and stops
    the pipeline. In eval/dev the check is advisory — a warning is stored in
    state so downstream agents can report it, but the pipeline continues.
    """

    instruction: str = ""
    tools: list = []

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        import os
        strict = os.environ.get("STRICT_PREFLIGHT", "false").lower() == "true"

        auth_result = verify_gcloud_auth()
        auth_data = json.loads(auth_result)

        if auth_data.get("status") != "ok":
            logger.warning(f"[{self.name}] gcloud auth issue: {auth_data}")
            if strict:
                yield Event(
                    author=self.name,
                    actions=EventActions(escalate=True),
                )
            else:
                # Store warning in state; pipeline continues so eval cases complete
                ctx.session.state["preflight_warning"] = auth_data.get("message", "gcloud not authenticated")
                yield Event(author=self.name)
        else:
            logger.info(f"[{self.name}] gcloud auth OK: {auth_data.get('active_account')}")
            ctx.session.state.pop("preflight_warning", None)
            yield Event(author=self.name)


# ═══════════════════════════════════════════════════════════════
# AGENT DEFINITIONS
# ═══════════════════════════════════════════════════════════════

# ── 1. Parameter Gatherer ─────────────────────────────────────
param_gatherer = LlmAgent(
    model=config.worker_model,
    name="param_gatherer",
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
    description=(
        "Extracts log analysis parameters from the user's request. "
        "Infers env, service, severity, freshness, and limit."
    ),
    instruction=f"""You are a parameter extraction specialist for GCP log analysis.

Given the user's request, extract these parameters:

| Param | Default | Description |
|-------|---------|-------------|
| env | (required) | GCP environment: {', '.join(config.env_map.keys())} |
| project | (required) | GCP project ID mapped from env using map below |
| service | (optional) | Service/container name filter |
| severity | ERROR | Minimum severity: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| freshness | 1h | Time window: 1h, 2h, 30m, 1d |
| limit | 500 | Max log entries to fetch |

**GCP Environment Map:**
{json.dumps(config.env_map, indent=2)}

**RULES:**
1. If env cannot be inferred from the user message, STOP and ask.
2. Map env to GCP project using the environment map above.
3. If severity is specified, use it; otherwise default to ERROR.
4. Output a structured JSON with all resolved parameters.

User request: {{{{user_request?}}}}
""",
    output_key="analysis_params",
)


# ── 2. Log Fetcher ────────────────────────────────────────────
log_fetcher = LlmAgent(
    model=config.worker_model,
    name="log_fetcher",
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
    description=(
        "Fetches logs from GCP Cloud Logging using gcloud CLI. "
        "Uses parameters from the param_gatherer."
    ),
    instruction="""You are a GCP log fetcher. Your job is to fetch logs using the provided parameters.

Read the 'analysis_params' state key for:
- project: GCP project ID
- env: GCP environment name (e.g., dev-vn, dev, test)
- severity: Minimum severity level
- freshness: Time window
- service_filter: Optional service filter
- limit: Max entries

**Steps:**
1. Call `fetch_gcp_logs` with the resolved parameters (including env)
2. Check the result status
3. If error, report it and stop
4. If success, report the count and file path

CRITICAL RULES:
- NEVER truncate silently. Always tell user if data was cut off.
- If the result set hits the limit, notify the user with exact count vs estimated total.
- If fetch fails, stop the workflow and report the error.
""",
    tools=[log_fetch_tool],
    output_key="fetch_result",
)


# ── 3. Log Analyzer ───────────────────────────────────────────
log_analyzer = LlmAgent(
    model=config.worker_model,
    name="log_analyzer",
    description=(
        "Analyzes fetched logs: groups errors, identifies patterns, "
        "computes severity breakdown, and finds top issues."
    ),
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
    instruction="""You are a meticulous log analyst. Analyze the fetched log file and produce a structured report.

Read 'fetch_result' state key for the log file path.

**Steps:**
1. Call `analyze_log_file` with the log file path from fetch_result
2. Review the analysis results
3. For each error group, provide a potential root cause based on the error message
4. Identify patterns: repeated errors, cascading failures, service-specific issues

**Output must include:**
- Severity breakdown (count per level)
- Top 5 error patterns with potential causes
- Affected services list
- Brief analysis summary

Output as structured JSON matching the LogAnalysisResult schema.
""",
    tools=[log_analyze_tool],
    output_key="log_analysis",
    after_agent_callback=collect_errors_callback,
)


# ── 4. Report Composer ────────────────────────────────────────
report_composer = LlmAgent(
    model=config.worker_model,
    name="report_composer",
    include_contents="none",
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
    description=(
        "Transforms log analysis into a professional investigation report "
        "with findings, recommendations, and actionable next steps."
    ),
    instruction="""You are an incident investigator. Transform the log analysis into a professional report.

---
### INPUT DATA
* Analysis Params: `{analysis_params}`
* Fetch Result: `{fetch_result}`
* Log Analysis: `{log_analysis}`

---

### REPORT STRUCTURE

## 1. Executive Summary
- 2-3 sentence summary of what was found
- Overall severity assessment (critical/high/medium/low)

## 2. Error Summary
- Total errors and warnings
- Severity breakdown (use a simple list or bullet points, do NOT use a table)
- Top 5 error patterns (use a numbered or bulleted list, do NOT use a table)

## 3. Detailed Findings
For each error group:
- Error pattern/message
- Count and frequency
- Affected services
- Potential root cause
- Sample log messages (bullet points)

## 4. Affected Services
- List of services/containers with errors
- Error count per service (use bullet points)

## 5. Recommendations
- Immediate actions to take
- Investigation steps
- Prevention measures

## 6. Raw Data Reference
- Log file path
- Time range analyzed
- GCP project and environment

---
### RULES
- NEVER use markdown tables anywhere in the report. Use clear bullet points or numbered lists instead.
- Every finding must have evidence from the logs.
- Never guess root cause without log evidence.
- State when evidence is insufficient.
- Be specific about affected services and error patterns.
- Include actionable recommendations.
- Avoid extensive whitespace padding or alignment spacing.
""",
    output_key="investigation_report",
    after_agent_callback=build_report_callback,
)


# ── 5. Report Saver ───────────────────────────────────────────
report_saver = LlmAgent(
    model=config.worker_model,
    name="report_saver",
    include_contents="none",
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
    description="Saves the investigation report to a markdown file.",
    instruction="""Save the investigation report to disk.

Report content:
{final_report}

Analysis params (contains env name):
{analysis_params}

Call `save_report` with:
- report_content: the final_report content above
- env: the environment name from analysis_params

Report the saved file path to the user.
""",
    tools=[report_save_tool],
    output_key="save_result",
)


# ═══════════════════════════════════════════════════════════════
# ORCHESTRATION PIPELINE
# ═══════════════════════════════════════════════════════════════

# The main log analysis pipeline
log_analysis_pipeline = _EvalSequentialAgent(
    name="log_analysis_pipeline",
    description=(
        "Executes a complete GCP log analysis. Checks auth, gathers parameters, "
        "fetches logs, analyzes errors, and composes an investigation report."
    ),
    sub_agents=[
        PreflightChecker(name="preflight_checker"),
        param_gatherer,
        log_fetcher,
        log_analyzer,
        report_composer,
        report_saver,
    ],
)

# The interactive coordinator (root agent)
log_analyst_coordinator = LlmAgent(
    name="log_analyst_coordinator",
    model=config.worker_model,
    generate_content_config=genai_types.GenerateContentConfig(temperature=0),
    before_agent_callback=init_coordinator_state,
    description=(
        "The primary log analysis assistant. Collaborates with the user to "
        "understand the investigation request, then executes the full analysis pipeline."
    ),
    instruction=f"""You are a Log Analyst and Incident Firefighter for GCP logs.

**YOUR JOB:**
1. Understand what the user wants to investigate
2. Extract environment and parameters
3. Delegate to the log analysis pipeline
4. Present findings clearly

**GCP ENVIRONMENT MAP:**
{json.dumps(config.env_map, indent=2)}

**TRIGGER PHRASES:**
- "why is X failing"
- "investigate logs"
- "analyze errors in dev-vn"
- "what hit prod last hour"
- "GCP alert — analyze"
- "check <service> logs"
- "investigate logs last 2h"

**WORKFLOW:**
1. **Understand**: Parse the user's request → identify env, service, time range
2. **Clarify**: If env is unclear, ask before proceeding
3. **Execute**: Delegate to log_analysis_pipeline
4. **Present**: After the pipeline completes, present the full investigation
   report to the user. If the pipeline stored a `final_report`, output it
   verbatim. Never end your turn with just a delegation message.

**RULES:**
- Never guess root cause without log evidence
- Always tell user if data was truncated
- Be specific about error patterns and affected services
- Include actionable recommendations
- ALWAYS present findings after the pipeline finishes

Current date: {datetime.datetime.now().strftime("%Y-%m-%d")}
""",
    sub_agents=[log_analysis_pipeline],
    output_key="final_response",
)


# ═══════════════════════════════════════════════════════════════
# ROOT AGENT & APP
# ═══════════════════════════════════════════════════════════════

root_agent = log_analyst_coordinator
app = App(root_agent=root_agent, name="app")
