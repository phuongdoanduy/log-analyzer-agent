# Log Analyzer Agent — Project Roadmap

## Current Status Summary

**Version:** 0.1.0  
**Release Date:** Q1 2026  
**Overall Progress:** ~40% complete (Phase 1 done, Phase 2 in progress)

## Phase Timeline

```
Phase 1: MVP Foundation       ✅ COMPLETE
├─ 5-agent pipeline           ✅ Done
├─ GCP log fetching           ✅ Done
├─ Error grouping             ✅ Done
└─ Report generation          ✅ Done

Phase 2: Testing & Eval       🔄 IN PROGRESS (30% done)
├─ Unit test suite            📝 Planned (test_dummy.py placeholder exists)
├─ Integration tests          ✅ Done (test_server_e2e.py)
├─ Eval dataset creation      📝 In progress
├─ Custom metrics             ✅ Done (3 metrics defined)
└─ Error deduplication        📝 Planned (callback framework ready)

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
- ✅ 5-agent sequential pipeline (param_gatherer → log_fetcher → log_analyzer → report_composer → report_saver)
- ✅ GCP log fetching via gcloud CLI
- ✅ Error grouping by message pattern (first 100 chars)
- ✅ Markdown report generation with findings
- ✅ FastAPI server with streaming support
- ✅ User feedback collection endpoint
- ✅ Docker image (python:3.12-slim, port 8080)
- ✅ Preflight authentication check
- ✅ Multi-environment support (dev-vn, dev, test, performance, prod)
- ✅ Severity classification (critical/high/medium/low)

### Key Metrics
- **Time to report:** <30 seconds for 500 logs
- **Error grouping:** Simple pattern-based (no false positives expected on MVP)
- **Deployable:** Docker, local dev, ready for Agent Runtime

## Phase 2: Testing & Evaluation — IN PROGRESS (30%)

### Objectives
Build robust test coverage, create eval datasets, and improve error deduplication.

### Current Progress

#### 2.1 Unit Test Suite (0% done)
**Status:** `test_dummy.py` is placeholder  
**Plan:**
1. Replace placeholder with real tests for:
   - config.py (env resolution, project lookup)
   - agent.py tools (verify_gcloud_auth, analyze_log_file, save_report)
   - app_utils/telemetry.py (OTel setup)
2. Target: >80% coverage on critical paths
3. Timeline: Week 1-2 of Phase 2

**Test Categories:**
```
tests/unit/
├── test_config.py           # Environment map, project resolution
├── test_agent_tools.py      # Tool functions (mock subprocess)
├── test_telemetry.py        # OTel setup
└── test_models.py           # Pydantic models (validation)
```

#### 2.2 Integration Tests (100% done)
**Status:** ✅ Implemented  
**Coverage:**
- E2E server startup and HTTP routes
- POST /run with analysis request (real gcloud call)
- POST /feedback endpoint
- FastAPI error handling

**File:** `tests/integration/test_server_e2e.py` (starts real FastAPI server)

#### 2.3 Eval Dataset Creation (40% done)
**Status:** 🔄 In progress  
**Plan:**
1. Create 3-5 canonical test cases (known error patterns)
2. Golden datasets: input logs + expected analysis results
3. Store in `tests/eval/datasets/`

**Example Test Case:**
```
Input: 50 "connection timeout" errors, 20 "auth failure" errors
Expected Output:
  - 2 error groups identified
  - Connection timeout group: 50 occurrences, CRITICAL severity
  - Auth failure group: 20 occurrences, HIGH severity
  - Report severity: HIGH
```

**Timeline:** Week 2-3 of Phase 2

#### 2.4 Custom Eval Metrics (100% done)
**Status:** ✅ Defined  
**Metrics:**
1. `env_resolution_accuracy` — param_gatherer resolves env correctly
2. `report_completeness` — report includes all error groups
3. `no_hallucinated_errors` — no errors invented by LLM

**Config:** `tests/eval/eval_config.yaml`

**Usage:** `agents-cli eval run` (generates traces, grades with metrics, compares)

#### 2.5 Error Deduplication (20% done)
**Status:** Framework ready, logic TBD  
**Current:** collect_errors_callback aggregates errors  
**Enhancement:** ML-based deduplication (Phase 3)

**Timeline:** Week 3-4 of Phase 2 (as improvement, not blocker)

### Phase 2 Success Criteria
- [ ] Unit tests pass (>80% coverage)
- [ ] Integration tests pass
- [ ] Eval dataset created (5+ test cases)
- [ ] Custom metrics implemented
- [ ] Error deduplication improved (feedback loop)

### Phase 2 Timeline
- **Start:** February 2026
- **Milestone 1 (Week 2):** Unit tests + coverage
- **Milestone 2 (Week 4):** Eval datasets + metrics
- **Target Completion:** End of February 2026

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

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | Feb 2026 | Initial MVP: 5-agent pipeline, report generation |
| 0.2.0 | Mar 2026 | Phase 2: Unit tests, eval, improved deduplication |
| 0.3.0 | Apr 2026 | Phase 3: ML clustering, multi-project, Slack |
| 0.4.0 | May 2026 | Phase 4: Agent Runtime, monitoring, GA |
| 1.0.0 | Jun 2026 | Production-ready, stable API |
