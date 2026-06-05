# Log Analyzer Agent — Architecture

## Agent Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOG ANALYZER AGENT                            │
│                    (Google ADK 2.x)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │            log_analyst_coordinator (LlmAgent)            │  │
│  │  • Understands user request                              │  │
│  │  • Extracts environment and parameters                   │  │
│  │  • Delegates to analysis pipeline                        │  │
│  │  • Presents findings to user                             │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         log_analysis_pipeline (SequentialAgent)          │  │
│  │                                                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │   param     │→ │    log      │→ │     log         │  │  │
│  │  │  gatherer   │  │   fetcher   │  │    analyzer     │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  │         │                │                 │             │  │
│  │         ▼                ▼                 ▼             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│  │  │  analysis   │  │   fetch     │  │   log_analysis  │  │  │
│  │  │   params    │  │   result    │  │   (structured)  │  │  │
│  │  │  (state)    │  │   (state)   │  │    (state)      │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│  │                                                          │  │
│  │  ┌─────────────────┐  ┌────────────────────────────────┐ │  │
│  │  │    report       │→ │        report_saver            │ │  │
│  │  │   composer      │  │  (saves to plans/reports/)     │ │  │
│  │  └─────────────────┘  └────────────────────────────────┘ │  │
│  │          │                      │                        │  │
│  │          ▼                      ▼                        │  │
│  │  ┌─────────────────┐  ┌────────────────────────────────┐ │  │
│  │  │ investigation   │  │      save_result              │ │  │
│  │  │    report       │  │        (state)                │ │  │
│  │  │   (state)       │  └────────────────────────────────┘ │  │
│  │  └─────────────────┘                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                        TOOLS LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐ │
│  │  verify_gcloud  │  │  fetch_gcp_logs │  │ analyze_log    │ │
│  │     _auth()     │  │      ()         │  │    _file()     │ │
│  │                 │  │                 │  │                │ │
│  │ • Check gcloud  │  │ • gcloud log    │  │ • Parse JSON   │ │
│  │   installed     │  │   read          │  │ • Group errors │ │
│  │ • Check auth    │  │ • Build filters │  │ • Severity     │ │
│  │ • Get project   │  │ • Save to JSON  │  │   breakdown    │ │
│  └─────────────────┘  └─────────────────┘  └────────────────┘ │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────────────────────────┐ │
│  │  save_report()  │  │  MCP: polaris-mcp-server (optional) │ │
│  │                 │  │                                     │ │
│  │ • Create dir    │  │ • gcloud-setup skill                │ │
│  │ • Write MD file │  │ • gcp-fetch-logs skill              │ │
│  │ • Return path   │  │ • log-analysis skill                │ │
│  └─────────────────┘  │ • root-cause-report skill           │ │
│                        └─────────────────────────────────────┘ │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                     GCP ENVIRONMENT MAP                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  dev-vn  │  │   dev    │  │   test   │  │   prod   │      │
│  │ klara-   │  │ klara-   │  │ klara-   │  │ klara-   │      │
│  │ nonprod  │  │ nonprod  │  │ nonprod  │  │   prod   │      │
│  │ asia-    │  │ europe-  │  │ europe-  │  │ europe-  │      │
│  │ southeast│  │ west6    │  │ west6    │  │ west6    │      │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│                                                                 │
│  ┌──────────────────┐                                          │
│  │   performance    │                                          │
│  │ klara-performance│                                          │
│  │    europe-west6  │                                          │
│  └──────────────────┘                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User Request
    │
    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   param     │────▶│    log      │────▶│    log      │
│  gatherer   │     │   fetcher   │     │   analyzer  │
└─────────────┘     └─────────────┘     └─────────────┘
    │                    │                    │
    ▼                    ▼                    ▼
analysis_params    fetch_result.json    log_analysis
(env, severity,    (raw GCP logs)       (error groups,
 freshness,                            severity,
 limit)                                patterns)
    │                    │                    │
    └────────────────────┴────────────────────┘
                         │
                         ▼
                ┌─────────────┐
                │   report    │
                │  composer   │
                └─────────────┘
                         │
                         ▼
                ┌─────────────┐
                │   report    │
                │   saver     │
                └─────────────┘
                         │
                         ▼
                plans/reports/
                log-analysis-<env>-<date>.md
```

## Session State Keys

| Key | Set by | Used by | Description |
|-----|--------|---------|-------------|
| `analysis_params` | param_gatherer | log_fetcher, report_composer | Extracted parameters |
| `fetch_result` | log_fetcher | log_analyzer | Fetch status and file path |
| `log_analysis` | log_analyzer | report_composer | Structured analysis results |
| `all_errors` | collect_errors_callback | — | Cumulative error database |
| `investigation_report` | report_composer | build_report_callback | Raw report content |
| `final_report` | build_report_callback | report_saver | Report with metadata header |
| `save_result` | report_saver | — | Saved file path |

## MCP Integration (Skill Driven Pattern)

The agent supports MCP integration with `polaris-mcp-server`. This follows the **Skill Driven** architecture pattern:

- MCP tools return **skill content** (Markdown guides)
- Agent reads the skill content and follows its instructions
- Skills are reusable across different agent implementations

### MCP Tools Available

| Tool | Returns | Agent Action |
|------|---------|--------------|
| `gcloud-setup` | Auth verification skill | Run verification bash commands |
| `gcp-fetch-logs` | Log fetching skill | Follow filter template and fetch command |
| `log-analysis` | Analysis methodology skill | Apply analysis on fetched logs |
| `root-cause-report` | Report template skill | Generate structured investigation report |

## Deployment Options

| Target | Command | Best For |
|--------|---------|----------|
| Local | `agents-cli playground` | Development and testing |
| Agent Runtime | `agents-cli deploy` | Managed GCP deployment |
| Cloud Run | `agents-cli deploy --deployment-target cloud_run` | Custom infra, event-driven |
| Docker | `docker build -t log-analyzer .` | Self-hosted |
