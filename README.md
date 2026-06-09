# Log Analyzer Agent

AI-powered GCP log analysis platform that automates incident investigation for DevOps and SRE teams.

**Status:** v0.1.0 (MVP) — 6-agent pipeline with preflight checks, log fetching, error analysis, and report generation.

## What It Does

- **Fetches logs** from GCP Cloud Logging (all 5 environments)
- **Groups errors** by message pattern; identifies severity and frequency
- **Generates reports** with executive summary, findings, and recommendations
- **Saves artifacts** to `plans/reports/` for audit and versioning
- **Provides API** for integration with incident management systems

## Quick Start (5 minutes)

### 1. Prerequisites
```bash
# Python 3.11+
python3 --version

# gcloud CLI authenticated (Application Default Credentials)
gcloud auth login --update-adc
gcloud config set project YOUR_PROJECT_ID
```

### 2. Install & Run
```bash
# Clone & install
git clone <repo-url> && cd log-analyzer-agent
uv sync

# Configure auth
cp .env.example .env
# Edit .env: set GOOGLE_CLOUD_PROJECT=your-project-id

# Test it
agents-cli run "analyze errors in dev-vn last 2 hours"
```

### 3. View Report
Reports are saved to `plans/reports/log-analysis-{env}-{timestamp}.md`

## Commands

### Development
| Command | Purpose |
|---------|---------|
| `adk web` | Interactive playground (web UI) |
| `agents-cli run "..."` | Quick one-off analysis |
| `adk api_server --port 8000` | Start API server |
| `pytest tests/` | Run tests |
| `agents-cli lint` | Lint code (ruff + ty + codespell) |

### Evaluation
| Command | Purpose |
|---------|---------|
| `agents-cli eval run` | Full eval (generate + grade) |
| `agents-cli eval generate` | Generate traces |
| `agents-cli eval grade` | Score traces |

### Deployment
| Command | Purpose |
|---------|---------|
| `docker build -t log-analyzer .` | Build Docker image |
| `agents-cli deploy` | Deploy to Agent Runtime |
| See `docs/deployment-guide.md` | Full deployment instructions |

## Architecture

**6-Agent Sequential Pipeline:**
```
log_analyst_coordinator
└── log_analysis_pipeline
    ├─ preflight_checker    → verify gcloud auth before analysis
    ├─ param_gatherer       → resolves environment, severity, freshness
    ├─ log_fetcher          → gcloud logging read + save JSON
    ├─ log_analyzer         → group errors, identify patterns (with extended thinking)
    ├─ report_composer      → generate markdown report
    └─ report_saver        → save to plans/reports/
```

For detailed diagrams: [docs/architecture.md](docs/architecture.md)

## Environment Support

| Environment | GCP Project | Region |
|-------------|-------------|--------|
| **dev-vn** | klara-nonprod | asia-southeast1-a |
| **dev** | klara-nonprod | europe-west6-a |
| **test** | klara-nonprod | europe-west6-a |
| **performance** | klara-performance | europe-west6-a |
| **prod** | klara-prod | europe-west6-a |

## Documentation

| Doc | Content |
|-----|---------|
| [README.md](README.md) | Quick start (this file) |
| [docs/architecture.md](docs/architecture.md) | Pipeline diagrams, data flow |
| [docs/codebase-summary.md](docs/codebase-summary.md) | Directory structure, modules |
| [docs/code-standards.md](docs/code-standards.md) | Python style, testing, ADK patterns |
| [docs/system-architecture.md](docs/system-architecture.md) | Agent design, session state, extensibility |
| [docs/project-overview-pdr.md](docs/project-overview-pdr.md) | Requirements, trade-offs, decisions |
| [docs/project-roadmap.md](docs/project-roadmap.md) | Phases, timeline, success metrics |
| [docs/deployment-guide.md](docs/deployment-guide.md) | Setup, local dev, cloud deployment |

## Project Status

**Phase 1 (Complete):** MVP pipeline ✅  
**Phase 2 (In Progress):** Unit tests, eval datasets 🔄  
**Phase 3 (Planned):** ML clustering, Slack integration 📋  
**Phase 4 (Planned):** Agent Runtime, monitoring, GA 📋  

See [docs/project-roadmap.md](docs/project-roadmap.md) for detailed timeline.

## Tech Stack

- **Framework:** Google ADK ≥1.15.0
- **Language:** Python 3.11+
- **Package Manager:** uv
- **Model:** Gemini 2.5 Flash
- **API:** FastAPI (via ADK)
- **Testing:** pytest + pytest-asyncio
- **Linting:** ruff + ty + codespell
- **Build:** hatchling

## Common Tasks

### Analyze Logs (One-Off)
```bash
agents-cli run "analyze ERROR logs in dev-vn last 6 hours"
```

### Start API Server (For Integrations)
```bash
adk api_server --port 8000
# POST /run with analysis request
```

### Deploy Locally in Docker
```bash
docker build -t log-analyzer .
docker run \
  -e GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e GOOGLE_CLOUD_LOCATION=global \
  -p 8080:8080 log-analyzer
```

### Deploy to Cloud
See [docs/deployment-guide.md](docs/deployment-guide.md) for full instructions:
- Cloud Run: `gcloud run deploy`
- Agent Runtime: `agents-cli deploy`
- Docker image push to GCR

### Run Tests
```bash
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration (starts server)
pytest                      # All tests
```

### Check Code Quality
```bash
agents-cli lint             # All linters
uv run ruff check --fix .   # Auto-fix issues
```

## Architecture Highlights

- **Multi-agent Pipeline:** Each agent has single responsibility
- **Session State Communication:** Decoupled agents via output_key
- **Tool Abstraction:** Reusable, mockable tools (verify_gcloud_auth, fetch_gcp_logs, etc.)
- **Callback Hooks:** Error deduplication, report finalization
- **Structured Models:** Pydantic validation for all data contracts
- **Error-First Design:** Fail fast with clear messages

For design details: [docs/system-architecture.md](docs/system-architecture.md)

## Development

### Setup
```bash
uv sync                    # Install all deps
uv sync --extra lint       # + linting tools
uv sync --extra eval       # + evaluation tools
```

### Code Standards
- Python 3.11+ with type hints on all public APIs
- Google-style docstrings
- ruff (E/F/W/I/C/B/UP/RUF rules, line-length=88)
- ty for type checking, codespell for spelling
- >80% test coverage target

See [docs/code-standards.md](docs/code-standards.md) for detailed standards.

### Adding Features
1. Read [docs/code-standards.md](docs/code-standards.md) → development patterns
2. Read [docs/system-architecture.md](docs/system-architecture.md) → extension points
3. Create feature branch
4. Implement + test
5. `agents-cli lint` + `pytest` must pass
6. Create PR

## Troubleshooting

### "gcloud: command not found"
Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install

### "Vertex AI auth failed"
```bash
gcloud auth login --update-adc
# Ensure .env has GOOGLE_GENAI_USE_VERTEXAI=TRUE and GOOGLE_CLOUD_PROJECT set
```

### "Unknown environment: xyz"
Use one of: dev-vn, dev, test, performance, prod

### Tests failing
```bash
pytest -v              # Verbose output
pytest --tb=short      # Short traceback
pytest --pdb           # Drop into debugger on failure
```

See [docs/deployment-guide.md](docs/deployment-guide.md) → Troubleshooting for more.

## Support

- **Questions:** See [docs/](docs/) for comprehensive guides
- **Bugs:** File GitHub issue with logs and reproduction steps
- **Features:** See [docs/project-roadmap.md](docs/project-roadmap.md) for planned work

## License

MIT

---

**Next Steps:**
- [Quick Deployment Guide](docs/deployment-guide.md) — Set up locally or in cloud
- [System Architecture](docs/system-architecture.md) — Understand agent design
- [Code Standards](docs/code-standards.md) — Development guidelines
- [Project Roadmap](docs/project-roadmap.md) — Planned features and timeline
