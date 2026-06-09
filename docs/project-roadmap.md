# Log Analyzer Agent — Project Roadmap

## Current Status Summary

**Version:** 0.1.0  
**Release Date:** February 2026  
**Current Date:** June 6, 2026  
**Overall Progress:** ~42% complete (Phase 1 done, Phase 2 in progress — 35% done)

## Phase Timeline

```
Phase 1: MVP Foundation       ✅ COMPLETE
├─ 6-agent pipeline           ✅ Done (with PreflightChecker)
├─ GCP log fetching           ✅ Done
├─ Error grouping             ✅ Done
└─ Report generation          ✅ Done

Phase 2: Testing & Eval       🔄 IN PROGRESS (35% done)
├─ Unit test suite            📝 Pending (0% — test_dummy.py placeholder)
├─ Integration tests          ✅ Done (100% — test_server_e2e.py)
├─ Eval dataset creation      🔄 In progress (70% — 8 test cases; ambiguous_env + clarification_followup)
├─ Custom metrics             ✅ Done (100% — 3 metrics defined)
├─ Error deduplication        📝 Pending (20% — callback framework ready)
└─ Agent instructions         ✅ Done (100% — fetch failure, grounding, anti-hallucination, completeness rules)

Phase 3: Advanced Features    📋 PLANNED
├─ ML-based clustering        📋 Design phase
├─ Multi-project analysis     📋 Design phase
├─ Slack/PagerDuty            📋 Design phase
├─ Persistent storage         📋 Design phase
└─ Custom severity rules      📋 Design phase

Phase 4: Deployment & GA      📋 PLANNED
├─ Agent Runtime setup        📋 In queue
├─ Monitoring/alerting        📋 In queue
├─ Load testing               📋 In queue
└─ Internal GA launch         📋 Target Q3 2026
```

## Phase 1: MVP Foundation — COMPLETE

### Objectives
Build a functional log analysis pipeline that fetches GCP logs, identifies error patterns, and generates reports.

### Completed Work (100%)
- ✅ 6-agent sequential pipeline (preflight_checker → param_gatherer → log_fetcher → log_analyzer → report_composer → report_saver)
- ✅ GCP log fetching via gcloud CLI
- ✅ Error grouping by message pattern (first 100 chars)
- ✅ Markdown report generation with findings
- ✅ FastAPI server with streaming support
- ✅ User feedback collection endpoint
- ✅ Docker image (python:3.12-slim, port 8080)
- ✅ Preflight authentication check (custom BaseAgent)
- ✅ Multi-environment support (dev-vn, dev, test, performance, prod)
- ✅ Severity classification (critical/high/medium/low)
- ✅ Extended thinking on log_analyzer (budget_tokens=5000)
- ✅ Callbacks for error deduplication and report finalization

### Key Metrics
- **Time to report:** <30 seconds for 500 logs
- **Error grouping:** Simple pattern-based (no false positives expected on MVP)
- **Deployable:** Docker, local dev, ready for Agent Runtime

## Phase 2: Testing & Evaluation — IN PROGRESS (30%)

### Objectives
Build robust test coverage, create eval datasets, and improve error deduplication.

### Current Progress

#### 2.1 Unit Test Suite (0% done — PENDING)
**Status:** `test_dummy.py` is placeholder  
**Plan:**
1. Replace placeholder with real tests for:
   - config.py (env resolution, project lookup)
   - agent.py tools (verify_gcloud_auth, analyze_log_file, save_report)
   - app_utils/telemetry.py (OTel setup)
2. Target: >80% coverage on critical paths
3. Estimated timeline: 2-3 weeks

**Test Categories:**
```
tests/unit/
├── test_config.py           # Environment map, project resolution
├── test_agent_tools.py      # Tool functions (mock subprocess, JSON parsing)
├── test_telemetry.py        # OTel setup and GCS integration
├── test_models.py           # Pydantic models (validation)
└── test_callbacks.py        # Error deduplication and report finalization
```

#### 2.2 Integration Tests (100% done)
**Status:** ✅ Implemented  
**Coverage:**
- E2E server startup and HTTP routes
- POST /run with analysis request (real gcloud call)
- POST /feedback endpoint
- FastAPI error handling

**File:** `tests/integration/test_server_e2e.py` (starts real FastAPI server)

#### 2.3 Eval Dataset Creation (70% done — IN PROGRESS)
**Status:** 🔄 In progress (8 test cases created; ambiguous and multi-turn cases added)
**Current State:**
1. ✅ 8 canonical test cases with known error patterns and behaviors
2. ✅ Golden datasets stored in `tests/eval/datasets/`
3. ✅ ambiguous_env case with rubric_groups: clarifies expected behavior (agent asks for env, does NOT fetch without clarification)
4. ✅ clarification_followup case: tests multi-turn flow where user provides env in follow-up message
5. 🔄 Ongoing refinement based on eval metric results

**Test Cases:**
1. dev_vn_error_analysis — Standard dev-vn analysis (2h window, ERROR severity)
2. prod_investigation — Production logs (1h, ERROR+CRITICAL)
3. service_specific — Service filter (dev-vn, luz-baumer service)
4. ambiguous_env — No env specified (expected: clarification question, no fetch)
5. custom_severity — WARNING logs (test environment, 30m window, severity-neutral language)
6. invalid_env — Invalid env name (expected: clear error message)
7. empty_logs — Time window with no logs (expected: empty result report)
8. clarification_followup — Multi-turn: ambiguous → clarification → user responds with "Check dev-vn" (expected: fetch + analysis)

**Remaining Work:** Validate all datasets run successfully, add more edge cases if needed

#### 2.4 Custom Eval Metrics (100% done)
**Status:** ✅ Defined  
**Metrics:**
1. `env_resolution_accuracy` — param_gatherer resolves env correctly
2. `report_completeness` — report includes all error groups
3. `no_hallucinated_errors` — no errors invented by LLM

**Config:** `tests/eval/eval_config.yaml`

**Usage:** `agents-cli eval run` (generates traces, grades with metrics, compares)

#### 2.5 Agent Instruction Refinements (100% DONE)
**Status:** ✅ Complete  
**Improvements:**
1. **log_fetcher** — Outputs 6-field error summary with `FETCH_STATUS: ERROR` sentinel on permission/auth/timeout failures
2. **log_analyzer** — Added GROUNDING RULE: all potential causes must cite pattern text + count from tool output; "cause unknown — needs investigation" when insufficient evidence
3. **report_composer** — Three additions:
   - FETCH FAILURE HANDLING: detects `FETCH_STATUS: ERROR`, generates 3-section "Analysis Incomplete" report
   - Severity-neutral language: "patterns/issues" not "errors" for WARNING/INFO/DEBUG severity
   - COMPLETENESS + ANTI-HALLUCINATION: all 6 sections always present; findings must trace to log_analysis data

**Impact:** Prevents hallucination, enables graceful error recovery, ensures report quality

#### 2.6 Error Deduplication (20% done — FRAMEWORK READY)
**Status:** Framework implemented, logic refinements pending  
**Current:** collect_errors_callback aggregates and deduplicates errors  
**Implementation:** Message prefix matching (first 100 chars) + dedup logic
**Enhancement Plan:** ML-based deduplication in Phase 3 if needed

**Remaining Work:** Performance testing on large datasets (1000+ logs)

### Phase 2 Success Criteria
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass ✅
- [ ] Eval dataset created (8 test cases, includes ambiguous + multi-turn) ✅
- [ ] Custom metrics implemented ✅
- [ ] Agent instructions refined (fetch failure, grounding, anti-hallucination) ✅
- [ ] Error deduplication improved (feedback loop)

### Phase 2 Timeline (Revised)
- **Start:** February 2026
- **Completed:** Integration tests (100%), custom metrics (100%), agent instructions (100%)
- **Current (June 6, 2026):** Eval datasets (70%), error dedup (20%), unit tests (0%)
- **Revised Target Completion:** End of June 2026

## Phase 3: Advanced Features — PLANNED

### Objectives
Reduce false positives, expand analysis scope, enable integrations.

### 3.1 ML-Based Error Clustering (Low Priority)
**Motivation:** Current grouping (first 100 chars) may miss semantically similar errors

**Approach:**
1. Embed error messages using a lightweight model
2. Cluster embeddings using DBSCAN or hierarchical clustering
3. Compare against pattern-based grouping (measure improvement)

**Success Metric:** Precision >98% (no false positive groups)

**Timeline:** Q2 2026 (if high false positive rates observed in Phase 2)

**Decision Point:** If <5% false positive rate on Phase 2 evals, defer to Phase 4

### 3.2 Multi-Project Analysis (Medium Priority)
**Motivation:** Analyze logs across multiple GCP projects simultaneously

**Scope:**
1. Accept list of environments (dev-vn + dev + test at once)
2. Fetch logs from all projects in parallel
3. Correlate errors across projects
4. Detect if issue is isolated to one project or systemic

**Effort:** 2-3 weeks (parallelization, correlation logic)

**Timeline:** Q2 2026

### 3.3 Slack/PagerDuty Integration (High Priority)
**Motivation:** Auto-post incident summaries to on-call channels

**Scope:**
1. FastAPI endpoint receives webhook from PagerDuty
2. Parse incident details (environment, service, time window)
3. Trigger analysis
4. Post summary to Slack #incidents channel
5. Include report link

**Effort:** 1-2 weeks (API integration, message formatting)

**Timeline:** Q2-Q3 2026

### 3.4 Persistent Session Storage (Medium Priority)
**Motivation:** Track analysis history, enable follow-ups

**Current:** In-memory sessions only (lost after request)

**Enhancement:**
1. Store sessions in PostgreSQL or Firestore
2. Enable "compare to previous analysis" queries
3. Track change over time (error frequency trends)
4. Archive reports with searchable metadata

**Effort:** 2-3 weeks (DB setup, schema design, query logic)

**Timeline:** Q3 2026

### 3.5 Custom Severity Rules (Low Priority)
**Motivation:** Different teams have different severity thresholds

**Scope:**
1. Admin interface to define rules per environment
2. Rules: "if error_count > X and error_type = 'auth', then CRITICAL"
3. Store in database
4. Apply in build_report_callback

**Effort:** 1-2 weeks

**Timeline:** Q3 2026

### Phase 3 Timeline
- **Q2 2026:** ML clustering (decision point), multi-project analysis, Slack integration
- **Q3 2026:** Persistent storage, custom rules, internal feedback loop

## Phase 4: Deployment & GA — PLANNED

### Objectives
Operationalize the agent for production use by SRE teams.

### 4.1 Agent Runtime Setup
**Status:** Code-ready, not yet deployed  
**Steps:**
1. Run `agents-cli deploy` to Agent Runtime
2. Configure environment (GOOGLE_GENAI_USE_VERTEXAI, GOOGLE_CLOUD_PROJECT, LOGS_BUCKET_NAME)
3. Set up monitoring dashboard
4. Configure CORS for web integrations

**Timeline:** Early Q3 2026

### 4.2 Monitoring & Alerting
**Status:** OTel framework in place, no alerts yet  
**Plan:**
1. Export metrics to Cloud Monitoring
2. Alerts: "analysis latency >45 seconds" or "gcloud auth failure"
3. Dashboard: request count, error rate, avg latency
4. Log analysis of user feedback (track satisfaction)

**Timeline:** Q3 2026

### 4.3 Load Testing
**Status:** Manual testing only  
**Plan:**
1. Load test: 10 concurrent analysis requests
2. Measure latency, error rate, resource usage
3. Identify bottlenecks (gcloud CLI, Gemini API, file I/O)
4. Optimize or scale based on findings

**Target SLA:** <45 second p95 latency, <1% error rate

**Timeline:** Q3 2026

### 4.4 Internal GA Launch
**Status:** Planning phase  
**Scope:**
1. Announce to SRE team via all-hands
2. Provide runbooks and examples
3. Gather feedback: "what's missing?", "what's not working?"
4. Iterate on feedback (bug fixes, UX improvements)

**Success Metric:** >50% of on-call rotation using agent by end of Q3

**Timeline:** Mid-Q3 2026

### Phase 4 Timeline
- **Week 1-2:** Agent Runtime deployment
- **Week 3-4:** Monitoring & alerting setup
- **Week 5-6:** Load testing
- **Week 7-8:** Internal GA + feedback collection
- **Target Completion:** End of Q3 2026

## Dependency & Blocker Chart

```
Phase 1 ✅
    ↓ (unblocks)
Phase 2 🔄 (in progress)
    ├─→ Unit tests (no blocker, parallel)
    ├─→ Eval datasets (no blocker, parallel)
    └─→ Custom metrics (done, no blocker)
    ↓ (completion unblocks)
Phase 3 📋 (waiting on Phase 2 completion)
    ├─→ ML clustering (optional, depends on feedback)
    ├─→ Multi-project (2-3 week feature, independent)
    ├─→ Slack integration (2 week feature, independent)
    ├─→ Persistent storage (2-3 week feature, independent)
    └─→ Custom rules (1-2 week feature, independent)
    ↓ (Phase 2 + 3 completion unblocks)
Phase 4 📋 (waiting on Phase 3 completion)
    ├─→ Agent Runtime (simple deploy, 1 day)
    ├─→ Monitoring (depends on deployment, 1 week)
    ├─→ Load testing (depends on deployment, 1 week)
    └─→ GA launch (depends on all above, 1 week)

Legend: ✅ Done | 🔄 In Progress | 📋 Planned
```

## Known Issues & Decisions Pending

### High Priority
1. **Unit Test Coverage** — test_dummy.py is placeholder, needs real tests
2. **Error Deduplication** — collect_errors_callback exists but logic needs refinement
3. **Eval Metrics** — defined but not yet run against real traces

### Medium Priority
1. **Error Grouping False Positives** — monitor in Phase 2, decide if ML needed
2. **Performance Optimization** — may need after load testing
3. **GCP Rate Limiting** — add more robust retry logic if issues observed

### Low Priority
1. **User Authentication** — not needed for internal GA, add later if public API
2. **Custom Severity Rules** — low demand signal, Phase 3 nice-to-have
3. **Alert Correlation** — future enhancement, not MVP

## Success Metrics by Phase

### Phase 1 Success (✅ Achieved)
- [ ] MVP shipped and functional
- [ ] 5-agent pipeline stable
- [ ] Local dev + Docker both work
- [ ] Manual testing passed

### Phase 2 Success (In Progress)
- [ ] >80% unit test coverage
- [ ] All integration tests pass
- [ ] Eval dataset created (5+ cases)
- [ ] Custom metrics operational
- [ ] False positive rate <5%

### Phase 3 Success (Planned)
- [ ] Feature decisions made (ML, multi-project, etc.)
- [ ] Features implemented per plan
- [ ] Phase 2 feedback incorporated

### Phase 4 Success (Planned)
- [ ] Deployed to Agent Runtime
- [ ] Monitoring dashboard live
- [ ] Load testing passed (p95 <45s)
- [ ] GA launched to SRE team
- [ ] >50% adoption by quarter end

## Roadmap Review Schedule

- **Weekly standups:** Status of Phase 2 tasks
- **Bi-weekly reviews:** Eval metric results, test coverage
- **Monthly retrospectives:** Lessons learned, adjust timeline

## Contact & Escalation

- **Project Lead:** [TBD]
- **SRE Partner:** [TBD]
- **Technical Questions:** See docs/system-architecture.md
- **Feature Requests:** File GitHub issue (Phase 3 candidates)

## Version History

| Version | Date | Status | Changes |
|---------|------|--------|---------|
| 0.1.0 | Feb 2026 | RELEASED | Initial MVP: 6-agent pipeline, report generation, FastAPI server |
| 0.2.0 | TBD | IN PROGRESS | Phase 2: Unit tests (pending), eval datasets (60%), improved deduplication |
| 0.3.0 | Q3 2026 | PLANNED | Phase 3: ML clustering, multi-project, Slack integration |
| 0.4.0 | Q4 2026 | PLANNED | Phase 4: Agent Runtime, monitoring, GA launch |
| 1.0.0 | 2027 | PLANNED | Production-ready, stable API, full monitoring |
