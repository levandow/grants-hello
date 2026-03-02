# Grants Hub

![CI](https://github.com/levandow/grants-hello/actions/workflows/ci.yml/badge.svg)

A backend service that collects, normalises, and exposes **grant opportunities** from Swedish and EU funding bodies through a single unified REST API.

**Stack:** Python 3.11 · FastAPI · PostgreSQL 16 · Docker Compose

> Full documentation: **[docs/guide.md](docs/guide.md)**

---

## Data sources

| Source | Description |
|--------|-------------|
| Vinnova | Swedish Innovation Agency |
| Formas | Research Council for Sustainable Development |
| Forte | Research Council for Health, Working Life and Welfare |
| VR | Swedish Research Council (Vetenskapsrådet) |
| EU FTOP | EU Funding & Tenders Portal (Horizon Europe) |

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/levandow/grants-hello.git
cd grants-hello

# 2. Create your env file
cp .env.example .env          # Linux/macOS/Git Bash
# Copy-Item .env.example .env  # PowerShell

# 3. Generate and set a secret key in .env
python -c "import secrets; print(secrets.token_hex(32))"
# Add the output as: SECRET_KEY=<value>

# 4. Start the stack
docker compose up --build
```

| URL | Description |
|-----|-------------|
| http://localhost:8080/health | Health check |
| http://localhost:8080/opportunities | Browse grants |
| http://localhost:8080/docs | Interactive API docs (Swagger UI) |

---

## Key environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | **Yes** | JWT signing secret — generate with `secrets.token_hex(32)` |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (default: localhost dev ports) |
| `VINNOVA_API_KEY` | For Vinnova | |
| `FORMAS_API_KEY` | For Formas | |
| `FORTE_API_KEY` | For Forte | |
| `VR_API_KEY` | For VR | |

See [`.env.example`](.env.example) for the full list including database settings.

---

## Common commands

```bash
docker compose up -d                  # Start in background
docker compose logs -f api            # View API logs
docker compose run --rm ingest        # Re-run data ingestion
docker compose down                   # Stop everything
docker compose down -v                # Full reset (deletes database)
docker compose up --build api         # Rebuild after requirements change
```

---

## API overview

```
GET  /health                  Health check
GET  /opportunities           List/search grants (filter, paginate, sort)
GET  /opportunities/{id}      Single opportunity
POST /opportunities           Upsert (used by ingestion)
GET  /facets                  Distinct filter values for UI
POST /token                   Login and receive a JWT token
POST /users/                  Register a new user
GET  /users/me/               Current user profile (requires token)
GET  /technologies/           List your technologies (requires token)
POST /technologies/           Register a technology (requires token)
POST /_seed                   Insert a demo record for testing
```

---

## Project structure

```
app/
├── main.py              API routes and startup
├── models.py            SQLAlchemy ORM models
├── schemas.py           Pydantic request/response schemas
├── crud.py              Database queries (search, upsert, facets)
├── security.py          JWT tokens and password hashing
├── normalize.py         Per-source record normalisation
├── normalize_utils.py   Shared normalisation helpers
└── connectors/          One connector module per data source

scripts/
└── ingest_any.py        Ingestion orchestrator (runs as Docker service)

tests/                   Pytest test suite
docs/
└── guide.md             Full developer and operator guide
```

---

## Development notes

- Python file changes in `app/` are picked up automatically (volume mount + `--reload`).
- After editing `requirements.txt`, rebuild: `docker compose up --build api`.
- Do **not** commit `.env` — it is in `.gitignore`.
- Run tests: `pytest tests/`
- On Windows PowerShell, use `curl.exe` instead of `curl`.

---

## License

