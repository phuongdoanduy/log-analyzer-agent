# Log Analyzer Agent — Project Overview & PDR

## Executive Summary

**log-analyzer-agent** is an AI-powered GCP log analysis platform that automates incident investigation for DevOps and SRE teams. It fetches logs from GCP Cloud Logging, identifies error patterns, groups similar errors, and generates structured investigation reports with root cause analysis and remediation recommendations.

**Problem Solved:** Manual log analysis is slow, error-prone, and requires deep GCP expertise. Teams waste hours manually searching logs, grouping errors, and writing incident reports.

**Solution:** A 5-agent pipeline that analyzes logs in seconds, surfaces critical error patterns, and generates actionable investigation reports.

## Target Users

1. **DevOps Engineers** — Investigating deployment failures, identifying affected services
2. **SRE Teams** — Root cause analysis for production incidents
3. **On-call Engineers** — Quick diagnostics during incidents to reduce MTTR
4. **Platform Teams** — Understanding health of multi-service GCP environments

## Product Requirements

### Functional Requirements

#### FR1: Multi-Environment Log Fetching
- Fetch logs from 5 GCP environments: dev-vn, dev, test, performance, prod
- Support severity filters: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Support time-based freshness: last 1h, 6h, 24h, 7d
- Limit results to configurable max log count (default 500)
- Optional service/container filtering by name

#### FR2: Intelligent Error Analysis
- Group similar errors by message pattern (first 100 characters)
- Calculate error frequency and severity distribution
- Track first and last seen timestamps for error groups
- Identify affected resources (services, containers, pods)
- Detect top 5 most common error patterns
- Provide sample messages for each error group

#### FR3: Root Cause Investigation
- Analyze error patterns for potential root causes
- Correlate errors across multiple services
- Suggest affected services list
- Generate executive summary of key findings

#### FR4: Structured Report Generation
- Markdown investigation reports with metadata
- Severity classification (critical/high/medium/low) based on error count
- Executive summary (2-3 sentences)
- Detailed findings with error groups and frequency
- Actionable recommendations
- Raw log file reference for manual inspection

#### FR5: Multi-Channel Access
- Interactive playground for ad-hoc analysis
- CLI interface for scripted/automated investigation
- API endpoint for integration with incident management systems
- User feedback collection for continuous improvement

### Non-Functional Requirements

#### NFR1: Performance
- Analyze 500+ logs in <30 seconds
- Generate reports in <5 seconds post-analysis
- API response time <45 seconds for typical queries
- Minimal memory footprint on long-running analysis

#### NFR2: Reliability
- Graceful error handling for gcloud CLI failures
- Retry logic for transient GCP API failures
- Validation of gcloud authentication before pipeline execution
- Clear error messages for missing or misconfigured environments

#### NFR3: Scalability
- Support in-memory session state (no persistent DB required)
- Handle multiple concurrent analysis requests
- Deployable on Agent Runtime or Docker
- Configurable resource allocation

#### NFR4: Security
- Require Google API key for Gemini access
- Use gcloud CLI for GCP authentication (no hardcoded credentials)
- Support CORS configuration for web integrations
- Log user feedback to Google Cloud Logging (audit trail)
- Optional telemetry upload to GCS (configurable)

#### NFR5: Maintainability
- Modular agent design (5 independent agents)
- Clear separation of concerns (tools, models, pipelines)
- Type hints and Pydantic models for data contracts
- ADK patterns for consistency and extensibility
- Comprehensive documentation and code comments

## Architecture Decisions

### Decision 1: Agent-Based Pipeline
**Chosen:** 5-agent sequential pipeline (param_gatherer → log_fetcher → log_analyzer → report_composer → report_saver)

**Rationale:**
- Separation of concerns: each agent has a single responsibility
- Extensibility: easy to insert/modify agents without breaking others
- Testing: can test agents independently
- ADK support: native SequentialAgent pattern with output_key communication

**Alternatives Rejected:**
- Single monolithic agent: harder to test, less maintainable
- Parallel agents: overkill for linear log→analyze→report workflow

### Decision 2: Session State as Communication Bus
**Chosen:** Use ADK's `output_key` for inter-agent data passing

**Rationale:**
- ADK native pattern: avoids workarounds
- Decoupled agents: no direct dependencies
- Visibility: state visible in session logs for debugging
- Atomicity: each agent's output is a single state entry

**Alternatives Rejected:**
- Direct agent-to-agent method calls: violates ADK patterns
- REST APIs between agents: adds network overhead and complexity

### Decision 3: Error Grouping by Message Pattern
**Chosen:** Group errors by first 100 characters of message

**Rationale:**
- Simple, deterministic grouping: no ML required for MVP
- Handles stack traces: first 100 chars captures key info before stack depth varies
- Fast: O(n) grouping with dict lookups
- Tunable: can adjust threshold (100 chars) without code changes

**Alternatives Rejected:**
- Fuzzy string matching: slower, more false negatives
- ML-based clustering: complex, overkill for MVP
- Stack trace parsing: fragile across languages

### Decision 4: Severity Based on Error Count
**Chosen:** Thresholds: critical >50, high >20, medium >5, low ≤5

**Rationale:**
- Simple rule: no ambiguity
- Business-aligned: volume correlates with impact
- Tunable: adjust thresholds in `build_report_callback()`

**Alternatives Rejected:**
- Keyword-based severity: fragile, language-dependent
- AI-driven classification: adds latency and complexity

### Decision 5: File-Based Report Output
**Chosen:** Save markdown reports to `plans/reports/log-analysis-{env}-{ts}.md`

**Rationale:**
- Version control friendly: can commit reports
- Archival: reports persist for audit
- Integration: easy to ingest into incident ticketing systems

**Alternatives Rejected:**
- In-memory reports only: lose history after session
- Database storage: requires persistent infra, adds operational burden

## Success Metrics

### Adoption
- Metric: Weekly active users (DevOps/SRE teams)
- Target: >50% of on-call rotation using agent by end of Q3

### Efficiency
- Metric: Time to generate incident report (vs. manual analysis)
- Target: <2 minutes automated vs. 15-30 minutes manual (10x improvement)
- Baseline: Measure on 10 recent incidents before deploy

### Accuracy
- Metric: Error groups correctly grouped (precision/recall)
- Target: >95% precision (false positive rate <5%)
- Measurement: Manual audit of 50 reports post-deploy

### Adoption Indicators
- Metric: Reports generated per week
- Target: >100 reports/week by month 2

## Implementation Roadmap

### Phase 1: MVP (Complete)
- ✅ 5-agent pipeline
- ✅ GCP log fetching (gcloud CLI)
- ✅ Error grouping and pattern analysis
- ✅ Markdown report generation
- ✅ FastAPI server with streaming
- ✅ User feedback endpoint

### Phase 2: Testing & Evaluation (In Progress)
- Real unit tests (replace test_dummy.py placeholder)
- Eval dataset creation and metrics
- Error deduplication improvements
- Integration with CI/CD pipelines

### Phase 3: Advanced Features (Planned)
- ML-based error clustering (reduce grouping false positives)
- Multi-project analysis (correlate errors across GCP projects)
- Slack/PagerDuty integration (auto-post incident summaries)
- Persistent session storage (track analysis history)
- Custom severity rules per environment
- Trace correlation (link errors to distributed traces)

### Phase 4: Deployment (Planned)
- Agent Runtime deployment (managed GCP)
- Monitoring and alerting (OTel metrics)
- Load testing and scaling validation
- Internal GA launch to SRE team
- Public API documentation

## Constraints & Assumptions

### Constraints
- Must use Google ADK (not other frameworks)
- Must support gcloud CLI for auth (no custom credential stores)
- Report generation must complete in <5 seconds
- Dev cluster must be accessible from deployment environment

### Assumptions
- User has gcloud CLI installed and authenticated
- Application Default Credentials configured (`gcloud auth login --update-adc`)
- GCP environments are stable and logs are queryable
- Error messages are meaningful (not completely random strings)
- Typical analysis window is 1-24 hours of logs

## Dependencies

### External Services
- Google Cloud Logging API (via gcloud CLI)
- Gemini API (gemini-2.0-flash model)
- (Optional) Google Cloud Storage (for telemetry)
- (Optional) Polaris MCP Server (for skill-based tools)

### Internal Dependencies
- Google ADK >=1.15.0 (framework)
- Python 3.11+ (language runtime)
- uv package manager (dependency management)

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| gcloud CLI not installed on deployment VM | High | Medium | Document prerequisites, check in PreflightChecker agent |
| GCP API rate limiting on large log queries | Medium | Low | Add retry logic with exponential backoff, respect limits |
| Gemini API token exhaustion | High | Low | Monitor token usage per request, implement request budgeting |
| Error grouping false positives (wrong groups) | Medium | Medium | Start with conservative thresholds, add ML in Phase 3 |
| Missing error context in 100-char pattern | Low | Low | Log full message in report, adjust pattern length if needed |

## Open Questions

1. Should we support custom error grouping rules per team? (Postpone to Phase 3)
2. What's the SLA for incident report generation? (<5 seconds, 30 seconds, 2 minutes?)
3. Should we auto-post to Slack, or just provide API? (Phase 4 decision)
4. Do we need to support log redaction for sensitive data? (Security req TBD)
5. Should phase 3 include alert correlation across multiple projects?

## Glossary

- **Error Group:** Set of similar errors grouped by message pattern
- **Analysis Params:** Environment, severity threshold, time freshness, log limit
- **Investigation Report:** Final markdown document with findings and recommendations
- **Severity Level:** Classification based on error count (critical/high/medium/low)
- **Telemetry:** Optional OpenTelemetry traces sent to GCS for monitoring
- **Session State:** In-memory key-value store shared across agents during analysis
