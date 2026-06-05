# Log Analyzer Agent — Deployment Guide

## Prerequisites

### System Requirements
- **Python:** 3.11 or later
- **gcloud CLI:** Latest version installed and authenticated
- **Internet:** Access to GCP APIs and Gemini API

### GCP Requirements
- **Logging Access:** Permission to read GCP Cloud Logging (roles/logging.viewer)
- **Gemini API:** Access to gemini-2.0-flash model
- **Service Account (if cloud deployment):** Service account with logging viewer role

### Local Development Prerequisites
```bash
# Install Python (if not present)
python3 --version  # Should be 3.11+

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Verify gcloud is installed
gcloud --version  # Should be v5.0+

# Authenticate with GCP
gcloud auth login --update-adc
gcloud config set project YOUR_PROJECT_ID
```

## Local Development Setup

### Step 1: Clone Repository
```bash
git clone <repo-url>
cd log-analyzer-agent
```

### Step 2: Install Dependencies
```bash
# Install all dependencies
uv sync

# Optional: install eval dependencies
uv sync --extra eval

# Optional: install lint dependencies
uv sync --extra lint
```

### Step 3: Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit .env and set your GCP project
nano .env
```

**Required Variables:**
```env
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

**Optional Variables:**
```env
LOGS_BUCKET_NAME=your-gcs-bucket-for-telemetry
ALLOW_ORIGINS=http://localhost:3000,http://localhost:8000
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT
```

### Step 4: Verify Setup
```bash
# Test gcloud auth
gcloud auth list
gcloud config get-value project

# Run a quick smoke test
agents-cli run "analyze errors in dev-vn last 1 hour"

# If successful, you'll see a report generated
```

## Running Locally

### Option 1: Interactive Playground
Best for exploration and testing:
```bash
adk web
# Opens web UI at http://localhost:8000
# Provides interactive chat interface with streaming responses
```

### Option 2: CLI Commands
Quick one-off analysis:
```bash
# Analyze dev environment last 2 hours
agents-cli run "analyze errors in dev-vn last 2 hours"

# Analyze with severity filter
agents-cli run "analyze ERROR and CRITICAL logs in prod last 6 hours"

# Analyze specific environment
agents-cli run "analyze errors in test last 24 hours"
```

### Option 3: API Server
For integration with other tools:
```bash
# Start ADK API server
adk api_server --port 8000

# Or use FastAPI directly
uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8000

# In another terminal, test the API
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"input": "analyze errors in dev-vn last 1 hour"}'
```

### Option 4: FastAPI with Auto-Reload
For development (hot-reload on code changes):
```bash
uvicorn app.fast_api_app:app --reload --port 8000
```

## Running Tests

### Unit Tests
```bash
# All unit tests
pytest tests/unit/

# Specific test file
pytest tests/unit/test_config.py -v

# With coverage report
pytest tests/unit/ --cov=app --cov-report=html
```

### Integration Tests
```bash
# All integration tests (starts real FastAPI server)
pytest tests/integration/ -v

# Specific test
pytest tests/integration/test_server_e2e.py::test_run_endpoint -v
```

### All Tests
```bash
# Run everything
pytest

# With coverage
pytest --cov=app
```

## Code Quality

### Linting
```bash
# Run all linters (ruff + ty + codespell)
agents-cli lint

# Or individually
uv run ruff check .
uv run ty check .
uv run codespell .

# Auto-fix ruff issues
uv run ruff check --fix .
```

### Type Checking
```bash
# Using ty (Astral's Rust-based checker)
uv run ty check .

# Notes: ty is conservative; some errors are informational
```

## Evaluation

### Create Baseline
```bash
# Generate eval traces
agents-cli eval generate

# Grade the traces with custom metrics
agents-cli eval grade

# View results
cat evals/latest/grades.json
```

### Compare to Previous Baseline
```bash
# After making changes, generate new traces
agents-cli eval generate

# Grade new traces
agents-cli eval grade

# Compare against baseline
agents-cli eval compare evals/baseline.json evals/latest/grades.json
```

## Docker Deployment

### Build Image
```bash
# Build locally
docker build -t log-analyzer:0.1.0 .

# Tag for GCR
docker tag log-analyzer:0.1.0 gcr.io/YOUR_PROJECT_ID/log-analyzer:0.1.0
```

### Run Container Locally
```bash
# Run with environment variables
docker run \
  -e GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e GOOGLE_CLOUD_LOCATION=global \
  -p 8080:8080 \
  log-analyzer:0.1.0

# Run with .env file
docker run --env-file .env \
  -p 8080:8080 \
  log-analyzer:0.1.0

# Test the running container
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"input": "analyze errors in dev-vn last 1 hour"}'
```

### Push to Google Container Registry (GCR)
```bash
# Configure authentication
gcloud auth configure-docker

# Push image
docker push gcr.io/YOUR_PROJECT_ID/log-analyzer:0.1.0

# Verify upload
gcloud container images list --repository=gcr.io/YOUR_PROJECT_ID
```

### Docker Troubleshooting
```bash
# View logs from container
docker logs <container_id>

# Run with interactive shell
docker run -it \
  -e GOOGLE_GENAI_USE_VERTEXAI=TRUE \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  log-analyzer:0.1.0 \
  /bin/bash

# Check image size
docker image ls log-analyzer
```

## Cloud Deployment — Agent Runtime

### Prerequisites
- Google Cloud project with Agent Runtime API enabled
- Service account with appropriate permissions
- Docker image pushed to GCR (see Docker Deployment above)

### Step 1: Enable Agent Runtime API
```bash
gcloud services enable agentbuilder.googleapis.com
```

### Step 2: Create Agent in Agent Runtime
```bash
# Deploy using agents-cli
agents-cli deploy

# Or manually via gcloud
gcloud agents create log-analyzer \
  --container-image-uri=gcr.io/YOUR_PROJECT_ID/log-analyzer:0.1.0 \
  --display-name="Log Analyzer Agent" \
  --description="GCP log analysis and incident investigation"
```

### Step 3: Set Environment Variables
```bash
# In Agent Runtime console or via gcloud
gcloud agents update log-analyzer \
  --update-env-variables \
  GOOGLE_GENAI_USE_VERTEXAI=TRUE,\
GOOGLE_CLOUD_PROJECT=your-project-id,\
GOOGLE_CLOUD_LOCATION=global,\
LOGS_BUCKET_NAME=your-bucket,\
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=NO_CONTENT
```

### Step 4: Test the Deployment
```bash
# Get agent endpoint
gcloud agents describe log-analyzer

# Make a request to the agent
curl -X POST https://YOUR_AGENT_ENDPOINT/run \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{"input": "analyze errors in dev-vn last 1 hour"}'
```

### Step 5: Monitor Agent
```bash
# View agent logs
gcloud logging read "resource.type=api" --limit 50

# View agent metrics
gcloud monitoring dashboards create \
  --config-from-file=monitoring-dashboard.json
```

## Cloud Deployment — Cloud Run

Alternative to Agent Runtime:

### Build and Push
```bash
# Build for Cloud Run (uses Dockerfile)
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/log-analyzer

# Or use Docker build + push
docker build -t gcr.io/YOUR_PROJECT_ID/log-analyzer .
docker push gcr.io/YOUR_PROJECT_ID/log-analyzer
```

### Deploy to Cloud Run
```bash
gcloud run deploy log-analyzer \
  --image gcr.io/YOUR_PROJECT_ID/log-analyzer \
  --platform managed \
  --region us-central1 \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID,GOOGLE_CLOUD_LOCATION=global" \
  --allow-unauthenticated
```

### View Logs
```bash
# Stream logs
gcloud run logs read log-analyzer --limit 50 --follow

# View metrics
gcloud run services describe log-analyzer
```

## Environment Variables Reference

### Required
| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Enable Vertex AI (ADC) auth | `TRUE` |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID for Vertex AI | `my-project-123` |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI region | `global` |

### Optional
| Variable | Description | Default |
|----------|-------------|---------|
| `LOGS_BUCKET_NAME` | GCS bucket for OTel telemetry | (disabled) |
| `ALLOW_ORIGINS` | CORS allowed origins | (all) |
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Set to `NO_CONTENT` to filter sensitive data | (capture all) |
| `COMMIT_SHA` | Git commit hash (Docker build arg) | (not set) |

### Deprecated (Do Not Use)
- `GCP_PROJECT` — Use gcloud config instead
- `GCLOUD_PATH` — gcloud found via PATH

## GCP Permissions Reference

### Roles Required

#### For gcloud CLI Authentication
```
roles/logging.viewer — Read access to Cloud Logging
```

#### For Service Account (Cloud Deployment)
```
roles/logging.viewer — Read logs from Cloud Logging
roles/storage.objectViewer — Read from GCS bucket (if telemetry enabled)
```

### Minimal Role Binding
```bash
# For service account (development)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/logging.viewer
```

## Monitoring & Health Checks

### Verify Gcloud Access
```bash
# Check installed gcloud version
gcloud --version

# Check authenticated account
gcloud auth list

# Check active project
gcloud config get-value project

# Test log reading
gcloud logging read "severity=ERROR" --limit 5
```

### Verify Vertex AI Access
```bash
# Test ADC credentials and Vertex AI access
gcloud auth application-default print-access-token
gcloud ml-engine models list --project YOUR_PROJECT_ID
```

### FastAPI Health Check
```bash
# If server is running on 8000
curl http://localhost:8000/health

# Check /docs for API documentation
curl http://localhost:8000/docs
```

### Docker Container Health
```bash
# Check if container is running
docker ps | grep log-analyzer

# View real-time resource usage
docker stats log-analyzer

# Check container logs
docker logs -f log-analyzer
```

## Troubleshooting

### "gcloud: command not found"
```bash
# Verify gcloud is installed
which gcloud

# If not found, install Google Cloud SDK
# macOS: brew install google-cloud-sdk
# Ubuntu: sudo apt-get install google-cloud-sdk
# Windows: Download from https://cloud.google.com/sdk/docs/install
```

### "Vertex AI auth failed"
```bash
# Re-authenticate ADC
gcloud auth login --update-adc

# Verify .env has required vars
grep GOOGLE_GENAI_USE_VERTEXAI .env
grep GOOGLE_CLOUD_PROJECT .env

# Test ADC access token
gcloud auth application-default print-access-token
```

### "Permission denied" reading logs
```bash
# Verify gcloud auth
gcloud auth list

# Re-authenticate if needed
gcloud auth login --update-adc

# Verify you have logging.viewer role
gcloud projects get-iam-policy YOUR_PROJECT_ID | grep logging.viewer

# Try reading a single log entry
gcloud logging read "severity=ERROR" --limit 1
```

### "connection timeout to database" in analysis
This is a legitimate error from logs, not a deployment issue. It indicates:
1. Analysis succeeded
2. Error was found in GCP logs
3. This error should appear in the generated report

### Server times out or hangs
```bash
# Check gcloud is responsive
timeout 5 gcloud logging read --limit 1

# Check Vertex AI latency
time gcloud auth application-default print-access-token

# If slow, may need to optimize or scale
```

## Performance Tuning

### Optimize Log Fetch
```python
# In param_gatherer or app.py, adjust:
default_limit = 100  # Reduce if timeouts
default_freshness = "1h"  # Narrow time window
```

### Optimize Report Generation
```python
# Reduce extended thinking budget in log_analyzer
planner=BuiltInPlanner(
    thinking_config=ThinkingConfig(budget_tokens=2000)  # Down from 5000
)
```

### Scale Deployment
```bash
# Cloud Run: increase concurrency
gcloud run deploy log-analyzer \
  --concurrency 100

# Cloud Run: increase memory
gcloud run deploy log-analyzer \
  --memory 1Gi
```

## Security Best Practices

### 1. Credential Management
```bash
# Use a dedicated service account in production (not user ADC)
gcloud iam service-accounts create log-analyzer-sa \
  --display-name="Log Analyzer Service Account"

# Grant Vertex AI access
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member=serviceAccount:log-analyzer-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/aiplatform.user

# Cloud Run picks up the attached service account automatically
```

### 2. CORS Configuration
```env
# Whitelist specific origins
ALLOW_ORIGINS=https://your-domain.com,https://incident-dashboard.internal
```

### 3. Authentication
```bash
# For Cloud Run, require authentication
gcloud run deploy log-analyzer \
  --no-allow-unauthenticated

# Caller must include OAuth token
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  https://log-analyzer-xxxxx.run.app/run
```

### 4. Audit Logging
```bash
# Enable Cloud Audit Logs for this service
gcloud services enable logging.googleapis.com

# View audit logs
gcloud logging read "protoPayload.serviceName=run.googleapis.com"
```

## Rollback Procedure

### If Deployment Fails

#### Cloud Run
```bash
# List previous revisions
gcloud run revisions list --service log-analyzer

# Rollback to previous version
gcloud run deploy log-analyzer \
  --image gcr.io/YOUR_PROJECT_ID/log-analyzer:previous-tag
```

#### Agent Runtime
```bash
# Rollback agent version
gcloud agents update log-analyzer \
  --container-image-uri=gcr.io/YOUR_PROJECT_ID/log-analyzer:previous-tag
```

## Deployment Checklist

Before deploying to production:

- [ ] All tests pass (`pytest`)
- [ ] Linting passes (`agents-cli lint`)
- [ ] Docker image builds (`docker build`)
- [ ] Docker image runs locally
- [ ] Environment variables set correctly
- [ ] gcloud authentication verified
- [ ] Vertex AI ADC credentials verified (`gcloud auth application-default print-access-token`)
- [ ] CORS origins whitelisted
- [ ] Monitoring dashboard created
- [ ] Rollback plan documented
- [ ] Team notified of deployment

## Support & Escalation

### Issues
1. Check this guide's Troubleshooting section
2. Check docs/system-architecture.md for design questions
3. Check docs/code-standards.md for code standards
4. File GitHub issue with logs and reproduction steps

### Logs Location
- **Local:** stdout from `agents-cli run` or `uvicorn`
- **Docker:** `docker logs <container_id>`
- **Cloud Run:** `gcloud run logs read log-analyzer`
- **Cloud Logging:** `gcloud logging read "resource.type=cloud_run_revision"`
- **Agent Runtime:** Agent Runtime console → Logs tab

### Performance Issues
1. Check gcloud latency: `time gcloud logging read --limit 1`
2. Check Gemini API: test with curl (see Troubleshooting)
3. Check Cloud Run memory: increase `--memory` flag
4. Profile with `--enable-profiler` (if supported by ADK)

## Next Steps

1. **Complete Deployment Guide:** You're here! ✅
2. **Read System Architecture:** docs/system-architecture.md (design details)
3. **Read Code Standards:** docs/code-standards.md (development guidelines)
4. **Read Roadmap:** docs/project-roadmap.md (upcoming features)
5. **Start Development:** `adk web` for interactive testing
