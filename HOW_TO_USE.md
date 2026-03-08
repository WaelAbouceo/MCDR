# How to Use MCDR CX Platform

This guide explains how to run the MCDR project locally or in Docker. It is based on the current codebase (not the README).

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for local frontend only)
- **Docker & Docker Compose** (optional, for Docker run)

---

## Option A: Run Locally

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

(Use a virtual environment if you prefer: `python -m venv myenv` then `myenv\Scripts\activate` on Windows.)

### 2. Generate mock data (first time only)

Scripts must run **from the correct directory** because they use relative paths for SQLite files.

**From project root:**

```bash
# Core + mobile DBs (50K investors) — run from mcdr_mock/
cd mcdr_mock
python generate_db.py
python generate_cx_data.py
cd ..

# Auth tables (roles + users with passwords)
python seed_poc.py
```

On Windows PowerShell you can set UTF-8 to avoid emoji errors:

```powershell
$env:PYTHONIOENCODING = "utf-8"
cd mcdr_mock; python generate_db.py; python generate_cx_data.py; cd ..
python seed_poc.py
```

### 3. Start the backend

```bash
uvicorn src.main:app --port 8100 --reload
```

### 4. Start the frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Frontend will be at **http://localhost:3000** (or 3001 if 3000 is in use). The dev server proxies `/api` to the backend on port 8100.

### 5. Open the app

- **Frontend:** http://localhost:3000 (or 3001)
- **API:** http://localhost:8100
- **API docs:** http://localhost:8100/docs

---

## Option B: Run in Docker (Development / POC)

Single command runs backend + frontend with SQLite mock data. No Node or local DB setup needed.

### First run (builds image and generates mock data)

```bash
docker compose -f docker-compose.dev.yml up --build
```

The first startup generates mock data (~20–30 seconds). When you see:

```text
==> Starting MCDR CX Platform on :8100 ...
INFO:     Uvicorn running on http://0.0.0.0:8100
```

open **http://localhost:8100** in your browser. The backend serves the built frontend; no separate frontend server.

### Later runs (data already in volume)

```bash
docker compose -f docker-compose.dev.yml up
```

### Stop

```bash
docker compose -f docker-compose.dev.yml down
```

### Reset mock data (delete DBs and regenerate on next up)

```bash
docker compose -f docker-compose.dev.yml down -v
docker compose -f docker-compose.dev.yml up --build
```

---

## Demo login credentials

| Role       | Username     | Password   |
|-----------|--------------|------------|
| Agent     | `agent1`     | `agent123` |
| Team Lead | `tl1`        | `lead123`  |
| Supervisor| `supervisor1`| `super123` |
| QA Analyst| `qa1`        | `qa1234`   |
| Admin     | `admin1`     | `admin123` |

---

## Troubleshooting

- **`no such table: cx_users`** — Run `generate_cx_data.py` from inside `mcdr_mock/` first, then `seed_poc.py` from the project root.
- **`no such table: investors`** — Run `generate_db.py` from inside `mcdr_mock/` before `generate_cx_data.py`.
- **Docker: “no such file or directory” for entrypoint** — The image was built with a script that had Windows line endings; rebuild after the fix (script uses LF).
- **Slow “All Cases” / tabs** — Pagination and backend optimizations are in place; ensure you’re on the latest code and that the backend is running (local or Docker).
