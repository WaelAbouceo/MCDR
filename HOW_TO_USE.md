# How to Use MCDR CX Platform

This guide explains how to run the MCDR project locally or in Docker.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** (for local frontend only)
- **Docker & Docker Compose** (required for MySQL)

---

## Option A: Run Locally (with Docker MySQL)

Even when running the app locally, MySQL runs in Docker. Start MySQL + phpMyAdmin first, then run the app natively.

### 1. Start MySQL + phpMyAdmin

```bash
docker compose -f docker-compose.dev.yml up mysql phpmyadmin redis -d
```

This starts:
- **MySQL** on port 3306 (databases: `mcdr_cx`, `mcdr_core`, `mcdr_mobile`, `mcdr_customer`)
- **phpMyAdmin** on http://localhost:8080
- **Redis** on port 6379

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

(Use a virtual environment if you prefer: `python -m venv myenv` then `myenv\Scripts\activate` on Windows.)

### 3. Generate mock data (first time only)

The scripts connect to MySQL using environment variables. Set them for local development:

```bash
# Linux / macOS
export MYSQL_HOST=localhost MYSQL_PORT=3306 MYSQL_USER=mcdr MYSQL_PASSWORD=mcdr_pass

# Windows PowerShell
$env:MYSQL_HOST = "localhost"; $env:MYSQL_PORT = "3306"; $env:MYSQL_USER = "mcdr"; $env:MYSQL_PASSWORD = "mcdr_pass"
```

Then run the seed scripts:

```bash
cd mcdr_mock
python generate_db.py
python generate_cx_data.py
cd ..
python seed_poc.py
```

### 4. Start the backend

```bash
uvicorn src.main:app --port 8100 --reload
```

### 5. Start the frontend (second terminal)

```bash
cd frontend
npm install
npm run dev
```

Frontend will be at **http://localhost:3000** (or 3001 if 3000 is in use). The dev server proxies `/api` to the backend on port 8100.

### 6. Open the app

- **Frontend:** http://localhost:3000 (or 3001)
- **API:** http://localhost:8100
- **API docs:** http://localhost:8100/docs
- **phpMyAdmin:** http://localhost:8080

---

## Option B: Run Everything in Docker

Single command runs MySQL + phpMyAdmin + Redis + backend + frontend. No local setup needed.

### First run (builds image and generates mock data)

```bash
docker compose -f docker-compose.dev.yml up --build
```

The first startup creates MySQL schemas and generates mock data (~30–60 seconds). When you see:

```text
==> Starting MCDR CX Platform on :8100 ...
INFO:     Uvicorn running on http://0.0.0.0:8100
```

Open the following in your browser:
- **App:** http://localhost:8100
- **phpMyAdmin:** http://localhost:8080

### Later runs (data persisted in MySQL volume)

```bash
docker compose -f docker-compose.dev.yml up
```

### Stop

```bash
docker compose -f docker-compose.dev.yml down
```

### Reset all data (delete MySQL volume and regenerate)

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

## phpMyAdmin

phpMyAdmin is available at **http://localhost:8080** and gives you full access to all four MySQL databases:

- `mcdr_cx` — CX operations (cases, calls, users, etc.)
- `mcdr_core` — Investor registry (investors, securities, holdings)
- `mcdr_mobile` — Mobile app users
- `mcdr_customer` — Customer profiles

Login: root / mcdr_root_pass (or mcdr / mcdr_pass for the app user).

---

## Troubleshooting

- **`Can't connect to MySQL server`** — Ensure Docker MySQL is running: `docker compose -f docker-compose.dev.yml up mysql -d`
- **`Table doesn't exist`** — MySQL init scripts run on first container start. If tables are missing, reset with `docker compose -f docker-compose.dev.yml down -v` and start again.
- **Docker: "no such file or directory" for entrypoint** — The image was built with a script that had Windows line endings; rebuild after the fix (script uses LF).
- **Slow "All Cases" / tabs** — Pagination and backend optimizations are in place; ensure you're on the latest code and that the backend is running.
