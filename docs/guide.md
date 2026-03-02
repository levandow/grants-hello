# Grants Hub — Developer & Operator Guide

**Version:** 1.0
**Stack:** Python 3.11 · FastAPI · PostgreSQL 16 · Docker Compose

---

## Table of Contents

1. [Overview](#1-overview)
2. [Prerequisites](#2-prerequisites)
3. [Quick Start](#3-quick-start)
4. [Environment Variables](#4-environment-variables)
5. [Running the Stack](#5-running-the-stack)
6. [API Reference](#6-api-reference)
7. [Authentication](#7-authentication)
8. [Data Ingestion](#8-data-ingestion)
9. [Project Structure](#9-project-structure)
10. [Running Tests](#10-running-tests)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Overview

Grants Hub is a backend service that collects, normalises, and exposes **grant opportunities** from multiple Swedish and EU funding bodies through a single unified REST API.

### Data sources

| Source | Type | Description |
|--------|------|-------------|
| **Vinnova** | Swedish | Innovation Agency — open calls via their public REST API |
| **Formas** | Swedish | Research Council for Sustainable Development |
| **Forte** | Swedish | Research Council for Health, Working Life and Welfare |
| **VR** | Swedish | Swedish Research Council (Vetenskapsrådet) |
| **EU FTOP** | European | EU Funding & Tenders Portal (Horizon Europe and others) |

All records are normalised into a common schema before storage, with multilingual fields (Swedish/English), unified status values (`Open`, `Forthcoming`, `Closed`), and structured deadlines.

---

## 2. Prerequisites

| Tool | Minimum version | Install |
|------|----------------|---------|
| **Docker Desktop** | 4.x | https://www.docker.com/products/docker-desktop |
| **Docker Compose** | v2 (bundled with Docker Desktop) | Included in Docker Desktop |
| **Git** | Any | https://git-scm.com |

> **Windows users:** All commands below work in PowerShell, Git Bash, or WSL2. For `curl` in PowerShell, use `curl.exe` (the built-in alias shadows the real curl).

---

## 3. Quick Start

```bash
# 1. Clone
git clone https://github.com/levandow/grants-hello.git
cd grants-hello

# 2. Create your local env file
#    Linux / macOS / Git Bash:
cp .env.example .env
#    PowerShell:
Copy-Item .env.example .env

# 3. Generate a secret key and paste it into .env as SECRET_KEY=<value>
python -c "import secrets; print(secrets.token_hex(32))"

# 4. Start everything
docker compose up --build
```

The API is now available at **http://localhost:8080**.

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Confirm the API is running |
| `GET /opportunities` | Browse grant opportunities |
| `GET /docs` | Interactive Swagger UI |
| `GET /redoc` | ReDoc API documentation |

---

## 4. Environment Variables

All configuration lives in a `.env` file at the project root. Copy `.env.example` to get started.

### Required

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing secret. **Never share or commit this.** Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |

### Database (match the `postgres` service in docker-compose.yml)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `grants` | Database user |
| `POSTGRES_PASSWORD` | `grants` | Database password |
| `POSTGRES_DB` | `grants` | Database name |
| `POSTGRES_HOST` | `postgres` | Hostname (use `postgres` inside Docker) |
| `POSTGRES_PORT` | `5432` | Port |

> **Note:** `db.py` reads its own set of env vars (`DB_HOST`, `DB_USER`, etc.). These are automatically satisfied by the `env_file` directive in `docker-compose.yml`.

### API

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8080` | Host port that the API is mapped to |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated list of allowed CORS origins. Do **not** use `*` when credentials are enabled. |

### Grant source API keys

| Variable | Required for |
|----------|-------------|
| `VINNOVA_API_KEY` | Vinnova connector |
| `FORMAS_API_KEY` | Formas connector |
| `FORTE_API_KEY` | Forte connector |
| `VR_API_KEY` | VR (Vetenskapsrådet) connector |

> The EU (FTOP) connector does not require an API key.

---

## 5. Running the Stack

### Start

```bash
docker compose up --build
```

Add `-d` to run in the background (detached mode):

```bash
docker compose up --build -d
```

### Stop

```bash
docker compose down
```

To also delete the database volume (full reset):

```bash
docker compose down -v
```

### View logs

```bash
# All services
docker compose logs -f

# API only
docker compose logs -f api

# Ingestion only
docker compose logs -f ingest
```

### Rebuild after code changes

The `api` service mounts `./app` as a volume and runs with `--reload`, so **Python file changes are picked up automatically** without a rebuild. If you add or remove Python packages (edit `requirements.txt`), you need to rebuild:

```bash
docker compose up --build api
```

### Running ingestion manually

The `ingest` service runs once at startup and then exits. To re-run it:

```bash
docker compose run --rm ingest
```

---

## 6. API Reference

The full interactive documentation is available at **http://localhost:8080/docs** (Swagger UI) or **http://localhost:8080/redoc**.

### `GET /health`

Returns `200 OK` if the API is running.

```json
{ "status": "ok" }
```

### `GET /opportunities`

List and search grant opportunities with filtering and pagination.

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` / `query` | string | Free-text search across title, summary, description |
| `status` | string | Filter by status: `Open`, `Forthcoming`, `Closed` |
| `source` | string | Filter by data source: `VINNOVA`, `EU`, `FORMAS`, `FORTE`, `VR` |
| `sponsor` | string | Filter by sponsoring organisation |
| `programme` | string | Filter by programme name |
| `tag` | string | Match a tag |
| `deadline_after` | `YYYY-MM-DD` | Only include calls closing after this date |
| `deadline_before` | `YYYY-MM-DD` | Only include calls closing before this date |
| `sort` | string | `recent` (default), `deadline_asc`, `deadline_desc` |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Results per page, 1–100 (default: 10) |

**Example — open EU calls closing after today:**

```bash
curl "http://localhost:8080/opportunities?source=EU&status=Open&sort=deadline_asc&page_size=5"
```

**Response:**

```json
{
  "items": [ { "id": "...", "title": {"en": "...", "sv": "..."}, "status": "Open", ... } ],
  "total": 142,
  "page": 1,
  "page_size": 5
}
```

### `GET /opportunities/{id}`

Fetch a single opportunity by its internal ID (e.g. `EU:HE-2025-123`).

### `POST /opportunities`

Upsert (create or update) a single opportunity. Idempotent — repeated calls with the same `source_uid` will update the existing record, not create a duplicate. Used internally by the ingest pipeline.

### `GET /facets`

Returns distinct values for use as filter options in a UI.

```json
{
  "sources": ["EU", "VINNOVA", "FORMAS"],
  "statuses": ["Open", "Forthcoming", "Closed"],
  "sponsors": [...],
  "programmes": [...]
}
```

### `POST /_seed`

Inserts a single demo opportunity. Useful for quickly verifying the database and API are working without running the full ingestion.

```bash
# PowerShell
curl.exe -X POST http://localhost:8080/_seed

# Bash / macOS
curl -X POST http://localhost:8080/_seed
```

---

## 7. Authentication

The API uses **JWT Bearer tokens** with a 30-minute expiry.

### Register a user

```bash
curl -X POST http://localhost:8080/users/ \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}'
```

### Obtain a token

```bash
curl -X POST http://localhost:8080/token \
  -F "username=you@example.com" \
  -F "password=yourpassword"
```

Response:

```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

### Use the token

Pass the token as a `Bearer` header on authenticated endpoints:

```bash
curl http://localhost:8080/users/me/ \
  -H "Authorization: Bearer eyJ..."
```

### Authenticated endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/me/` | GET | Get the current user's profile |
| `/technologies/` | GET | List your technologies |
| `/technologies/` | POST | Register a new technology (TRL 1–9) |

---

## 8. Data Ingestion

### How it works

The ingestion pipeline (in `scripts/ingest_any.py`) runs as the `ingest` Docker service:

1. Waits for the API to be healthy (up to 90 seconds)
2. Fetches records from each configured data source
3. Normalises each record into the unified schema via `app/normalize.py`
4. POSTs each record to `POST /opportunities` (upsert — safe to re-run)

### Data sources and connectors

| Source | Connector | Fetch method |
|--------|-----------|-------------|
| Vinnova | `app/connectors/vinnova_rounds.py` | REST API, date-filtered |
| EU FTOP | `app/connectors/eu_ftop.py` | Paginated search API, 100 per page |
| Formas | `app/connectors/formas.py` | REST API, requires `FORMAS_API_KEY` |
| Forte | `app/connectors/forte.py` | REST API, requires `FORTE_API_KEY` |
| VR | `app/connectors/vr.py` | REST API, requires `VR_API_KEY` |

### Re-running ingestion

Ingestion is safe to repeat — the upsert mechanism prevents duplicate records. To re-fetch all sources:

```bash
docker compose run --rm ingest
```

### Running a single source manually

```python
# From the project root, with the API already running:
from app.connectors.vinnova_rounds import fetch
from app.normalize import normalize
import requests

for rec in fetch():
    n = normalize(rec, source="VINNOVA")
    requests.post("http://localhost:8080/opportunities", json=n)
```

### Normalisation

Each source's records are mapped to a common schema by `app/normalize.py`. The shared helper functions live in `app/normalize_utils.py`. The unified schema includes:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Globally unique ID: `{SOURCE}:{source_uid}` |
| `source_uid` | string | Identifier within the source system |
| `source` | string | `VINNOVA`, `EU`, `FORMAS`, `FORTE`, `VR` |
| `title` | `{sv, en}` | Multilingual title dict |
| `summary` | `{sv, en}` | Multilingual summary dict |
| `status` | string | `Open`, `Forthcoming`, `Closed`, `Unknown` |
| `opens_at` | `YYYY-MM-DD` | Opening date |
| `closes_at` | `YYYY-MM-DD` | Closing/deadline date |
| `deadlines` | list | All deadline objects with `{type, date}` |
| `links` | `{landing, apply}` | URLs as strings |
| `documents` | list | Attached PDFs / formal documents |
| `contacts` | list | Contact persons |

---

## 9. Project Structure

```
grants-hello/
├── app/                        # FastAPI application
│   ├── main.py                 # API routes and startup
│   ├── models.py               # SQLAlchemy ORM models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── crud.py                 # Database queries (search, upsert, facets)
│   ├── db.py                   # Database connection and session
│   ├── security.py             # JWT tokens and password hashing
│   ├── normalize.py            # Record normalisation (per-source logic)
│   ├── normalize_utils.py      # Shared normalisation helpers
│   └── connectors/             # One file per data source
│       ├── base.py             # Connector protocol (interface definition)
│       ├── vinnova_rounds.py   # Vinnova API
│       ├── eu_ftop.py          # EU Funding & Tenders Portal
│       ├── formas.py           # Formas
│       ├── forte.py            # Forte
│       └── vr.py               # VR (Vetenskapsrådet)
│
├── scripts/
│   ├── ingest_any.py           # Main ingestion orchestrator
│   └── view_*.py               # Debugging / inspection utilities
│
├── tests/                      # Test suite (pytest)
│   ├── test_normalize.py
│   ├── test_security.py
│   ├── test_eu_fetch.py
│   └── test_vinnova_fetch.py
│
├── docs/
│   └── guide.md                # This document
│
├── docker-compose.yml          # Service orchestration
├── Dockerfile                  # API container image
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
└── .env                        # Your local config (never commit this)
```

---

## 10. Running Tests

Tests use **pytest** and run outside Docker (directly on your machine or in CI).

### Install dependencies locally

```bash
pip install -r requirements.txt
pip install pytest
```

### Run all tests

```bash
pytest tests/
```

### Run a specific test file

```bash
pytest tests/test_normalize.py -v
```

> **Note:** Tests that hit the live API or database require the stack to be running. Tests in `test_normalize.py` and `test_security.py` are self-contained and can run offline.

---

## 11. Troubleshooting

### API fails to start with `SECRET_KEY environment variable is not set`

Your `.env` file is missing the `SECRET_KEY` variable. Open `.env` and add:

```
SECRET_KEY=<generated value>
```

Generate a value with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### `docker compose up` fails with a port conflict

Another process is using port 8080 or 54320. Either stop that process or change the port in `.env`:

```
API_PORT=9090
```

Then restart with `docker compose up`.

### Database connection refused

The API connects to the `postgres` service by hostname. If you run the API outside Docker (e.g. `uvicorn` directly on your machine), the hostname `postgres` won't resolve. Override it:

```bash
DB_HOST=localhost DB_PORT=54320 uvicorn app.main:app --reload
```

### Ingestion exits with no data

Check that the relevant API keys are set in `.env`. The connectors for Formas, Forte, and VR will return an empty list silently if the key is missing. The EU connector requires no key. Vinnova uses `VINNOVA_API_KEY`.

Run the ingest service in the foreground to see detailed output:

```bash
docker compose run --rm ingest
```

### `curl` is not working in PowerShell

PowerShell's built-in `curl` is an alias for `Invoke-WebRequest`. Use `curl.exe` instead to invoke the real curl binary:

```powershell
curl.exe http://localhost:8080/health
curl.exe -X POST http://localhost:8080/_seed
```

### Opportunity statuses look wrong

Status is computed at ingestion time from the opening and closing dates. If an opportunity shows as `Closed` but the source API says it is `Open`, re-run ingestion to pull the latest data:

```bash
docker compose run --rm ingest
```

---

*This guide covers the current development state of Grants Hub. For questions or issues, open a ticket on GitHub.*
