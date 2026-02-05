# 📑 Grants Hub (Hello Backend)

![CI](https://github.com/levandow/grants-hello/actions/workflows/ci.yml/badge.svg)

A minimal backend prototype for collecting and harmonizing **grant opportunities** from Sweden, the EU, and other sources.  
Built with **FastAPI** + **PostgreSQL** and containerized with **Docker Compose**.

---

## ✨ Features
- 🌐 REST API powered by FastAPI  
- 🗄 PostgreSQL database with SQLAlchemy ORM  
- 🔄 Unified data schema for grant opportunities  
- ⚙️ CI pipeline on GitHub Actions (builds & runs health check)
- 🧪 Simple seed endpoint for demo/testing
- 🎯 Facet endpoint for dynamic filter options
- 🔒 `.env` support (with example file)

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/levandow/grants-hello.git
cd grants-hello
```

### 2. Copy environment variables
Create your own `.env` file based on the example:

Linux/Mac:
```bashv
cp .env.example .env
```

Windows PowerShell:
```powershell
Copy-Item .env.example .env
```

Edit `.env` if you want to change database credentials or ports.

### 3. Build and run
```bash
docker compose up --build
```

The API will be available at:

- Health check → [http://localhost:8080/health](http://localhost:8080/health)  
- Opportunities → [http://localhost:8080/opportunities](http://localhost:8080/opportunities)

### 4. (Optional) Seed demo data
To insert a sample opportunity:

PowerShell:
```powershell
curl.exe -X POST http://localhost:8080/_seed
```

Then check the data:
```powershell
curl.exe http://localhost:8080/opportunities
```

---

## 📦 Project Structure
```
.
├── app/
│   ├── main.py        # FastAPI entrypoint
│   ├── db.py          # Database connection/session
│   ├── models.py      # SQLAlchemy models
│   ├── schemas.py     # Pydantic schemas
│   └── crud.py        # Data access methods
├── docker-compose.yml # API + Postgres stack
├── Dockerfile         # API container
├── requirements.txt   # Python dependencies
├── .env.example       # Example environment variables
└── .github/workflows/ci.yml  # GitHub Actions pipeline
```

---

## 🛠 Development Notes
- Do **not** commit your `.env` — it’s ignored by `.gitignore`.  
- Update `.env.example` if new variables are added.  
- On Windows, use `curl.exe` instead of `curl` in PowerShell.  
- To stop the stack:  
  ```bash
  docker compose down
  ```

---

## ✅ Roadmap
- [x] FastAPI + PostgreSQL skeleton  
- [x] CI build & health check  
- [ ] Add ingestion scripts for Swedish & EU grant APIs  
- [ ] Normalize multi-language text fields  
- [ ] Add search/filter endpoints  
- [ ] Connect to a frontend (Lovable)  

---

## 📜 License

