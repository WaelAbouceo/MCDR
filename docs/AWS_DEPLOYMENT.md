# Hosting MCDR on AWS

This guide covers ways to run the MCDR CX Platform on AWS. Choose based on your needs: **single EC2** (simplest), **EC2 + Docker Compose** (PostgreSQL/Redis), or **ECS + RDS** (scalable production).

---

## Prerequisites

- AWS account with permissions to create EC2, security groups, and (optionally) RDS, ECS, ElastiCache
- Docker installed locally (to build the image)
- (Optional) A domain name and SSL certificate for HTTPS

---

## Option 1: Single EC2 with Docker (simplest)

Best for: demos, internal use, or a first deployment. One server runs the app and serves both API and frontend. SQLite and in-memory rate limiting are used (no Redis required for a single instance).

### 1. Build the image locally

From the project root:

```bash
docker build -t mcdr-cx:latest .
```

### 2. Launch an EC2 instance

- **AMI**: Amazon Linux 2023 or Ubuntu 22.04
- **Instance type**: e.g. `t3.small` (2 vCPU, 2 GB RAM)
- **Storage**: 20–30 GB
- **Security group**: allow inbound **22** (SSH), **80** (HTTP), and **443** (HTTPS if you use a reverse proxy)

### 3. Install Docker on the instance

**Amazon Linux 2023:**

```bash
sudo yum update -y
sudo yum install -y docker
sudo systemctl enable docker && sudo systemctl start docker
sudo usermod -aG docker ec2-user
# Log out and back in so the group takes effect
```

**Ubuntu:**

```bash
sudo apt update && sudo apt install -y docker.io
sudo systemctl enable docker && sudo systemctl start docker
sudo usermod -aG docker ubuntu
```

### 4. Prepare environment and run the container

Create a directory and an env file on the server (e.g. `/home/ec2-user/mcdr`):

```bash
mkdir -p ~/mcdr/data
cd ~/mcdr
nano .env
```

**.env** (adjust values; required for production):

```env
ENVIRONMENT=production
SECRET_KEY=<generate-with: python3 -c "import secrets; print(secrets.token_hex(32))">
CORS_ORIGINS=https://your-domain.com
# Or for testing with IP: http://YOUR_EC2_PUBLIC_IP

# SQLite paths inside the container (we mount a volume)
MCDR_CX_DB_PATH=/data/mcdr_cx.db
MCDR_CORE_DB_PATH=/data/mcdr_core.db
MCDR_MOBILE_DB_PATH=/data/mcdr_mobile.db
DATABASE_URL=sqlite+aiosqlite:////data/mcdr_cx.db
CUSTOMER_DB_URL=sqlite+aiosqlite:////data/mcdr_cx.db
```

The app expects DB files under `/data` in the container. Copy your existing SQLite DBs into `~/mcdr/data/` (e.g. from `mcdr_mock/`) or run the seed after first start (see below).

Run the container:

```bash
docker run -d \
  --name mcdr \
  -p 80:8000 \
  -v $(pwd)/data:/data \
  --env-file .env \
  --restart unless-stopped \
  mcdr-cx:latest
```

**Note:** The default Dockerfile uses `/app/frontend/dist` and the app’s default DB paths. If your image was built with paths under `mcdr_mock/`, you can override with env vars so the app uses `/data`:

- Ensure `mcdr_cx.db` (and optionally `mcdr_core.db`, `mcdr_mobile.db`) exist in `~/mcdr/data/`.  
- **Option A — Create DBs on the server:** run the init script (no need to copy files): see [Create databases on EC2](#create-databases-on-ec2) below.  
- **Option B — Copy from your machine:** `scp mcdr_mock/mcdr_cx.db ec2-user@YOUR_EC2_IP:~/mcdr/data/`.

### 5. Create databases on EC2

If you did not copy DB files, you can generate them on the server so the app has schema and seed data (including demo logins):

```bash
cd ~/MCDR
chmod +x scripts/init_db_ec2.sh
./scripts/init_db_ec2.sh data
```

This script (1) creates `mcdr_core.db` and `mcdr_mobile.db`, (2) creates `mcdr_cx.db` with cases, calls, and CX users, (3) seeds auth (roles and test users with passwords). Step 2 may take 2–5 minutes. Requires Python 3 and pip; the script installs `faker` and `bcrypt` if needed. After it finishes, set permissions and restart the container:

```bash
chmod 666 data/*.db
docker restart mcdr
```

### 6. Seed the database (if you only copied empty or partial DBs)

If you already have `mcdr_cx.db` with `cx_users` but no auth tables, run:  
`MCDR_CX_DB_PATH=/home/ubuntu/MCDR/data/mcdr_cx.db python3 seed_poc.py` from the repo root. Otherwise use the init script above to create everything.

### 7. Open the app

- **HTTP**: `http://YOUR_EC2_PUBLIC_IP/`  
- **HTTPS**: Put a reverse proxy (e.g. nginx or Caddy) in front of the container and point your domain to the EC2 IP; set `CORS_ORIGINS` to that domain.

---

## Option 2: EC2 with Docker Compose (PostgreSQL + Redis)

Best for: a production-like setup on one machine with PostgreSQL and Redis.

### 1. Build and prepare on EC2

- Install Docker and Docker Compose on the instance (as in Option 1).
- Clone the repo or copy the project (including `docker-compose.yml`, `nginx.conf`, `Dockerfile`, `db/`, and `.env`) onto the server.

### 2. Populate frontend for nginx

The Compose file uses nginx to serve the frontend. Build it and feed it to the nginx volume:

```bash
cd frontend && npm ci && npm run build && cd ..
# Copy built assets into a volume or bind mount used by nginx (see below)
```

For a simple approach: build the frontend in the `api` image (the Dockerfile already does this). Then either:

- Use a single container that serves both API and frontend (the app now serves the SPA from the same image when `frontend/dist` exists), or  
- Copy `frontend/dist` into a directory that you mount into the nginx service (e.g. a host path or a volume you populate).

Example **docker-compose.override.yml** (optional) to use a host path for the frontend:

```yaml
services:
  nginx:
    volumes:
      - ./frontend/dist:/usr/share/nginx/html:ro
```

Then run `npm run build` in `frontend/` on the server and start Compose.

### 3. Environment variables

Create `.env` with at least:

```env
ENVIRONMENT=production
SECRET_KEY=<at-least-32-char-random-key>
CORS_ORIGINS=https://your-domain.com

CX_DB_PASSWORD=<strong-password>
CUSTOMER_DB_PASSWORD=<strong-password>

DATABASE_URL=postgresql+asyncpg://mcdr:CX_DB_PASSWORD@cx-db:5432/mcdr
CUSTOMER_DB_URL=postgresql+asyncpg://mcdr_readonly:CUSTOMER_DB_PASSWORD@customer-db:5432/mcdr_customers
REDIS_URL=redis://redis:6379/0
```

Use the same values as in `docker-compose.yml` for service names and DB names.

### 4. Run

```bash
docker compose up -d
```

Ensure the DB init scripts in `db/` run (e.g. via `docker-entrypoint-initdb.d`). Open the app on port 80 (or the port nginx is mapped to).

---

## Option 3: ECS Fargate + RDS (production-style)

Best for: scalable, managed production with separate DB and cache.

- **API**: Run the Docker image as an ECS Fargate service behind an Application Load Balancer (ALB).
- **Frontend**: Either served by the same container (SPA mounted in the image) or built and deployed to **S3 + CloudFront** with `VITE_API_BASE_URL` pointing at the ALB URL.
- **Database**: Amazon RDS (PostgreSQL); use the same schema as in `db/init_cx.sql` and point `DATABASE_URL` and `CUSTOMER_DB_URL` at RDS.
- **Redis**: ElastiCache (optional) for rate limiting and token store; set `REDIS_URL`.
- **Secrets**: Store `SECRET_KEY` and DB passwords in **AWS Secrets Manager** or **Systems Manager Parameter Store** and inject them into the ECS task definition.

High-level steps:

1. Create a VPC (or use default), RDS PostgreSQL instance(s), and optionally ElastiCache Redis.
2. Build and push the Docker image to **Amazon ECR**.
3. Create an ECS cluster, task definition (using the image, env, and secrets), and Fargate service behind an ALB.
4. Set `CORS_ORIGINS` to your frontend origin (e.g. CloudFront or the ALB URL if the SPA is served from the same service).
5. (Optional) Put the SPA in S3, fronted by CloudFront, and set `VITE_API_BASE_URL` to the API base URL.

---

## Security checklist

- Use a **strong SECRET_KEY** (≥32 characters); generate with  
  `python3 -c "import secrets; print(secrets.token_hex(32))"`.
- Set **ENVIRONMENT=production** so `/docs` is disabled and production checks apply.
- Set **CORS_ORIGINS** to your real frontend origin(s); no `localhost` in production.
- Prefer **HTTPS** (ALB with ACM certificate or a reverse proxy with Let’s Encrypt).
- Restrict **security groups** to the minimum required (e.g. 80/443 from the internet; 22 only from your IP or a bastion).
- For production data, use **RDS** (and optionally ElastiCache) instead of SQLite.

---

## Troubleshooting

| Issue | What to check |
|-------|----------------|
| 502 / connection refused | Container not listening on 8000; check `docker logs mcdr`. |
| Blank page or API 404 | Frontend is calling the correct origin; if using same origin, API is under `/api`. |
| Login fails | DB has users (run seed); `SECRET_KEY` is set and consistent. |
| CORS errors | `CORS_ORIGINS` includes the exact origin the browser uses (scheme + host + port). |
| Health check fails | `/health` and `/health/ready`; for ready, DB (and Redis if used) must be reachable. |

---

## CI/CD: Deploy on push to main

To deploy automatically when you push to `main`, see **[DEPLOY_EC2_CI.md](./DEPLOY_EC2_CI.md)**. You’ll add GitHub Actions secrets (`EC2_HOST`, `EC2_SSH_KEY`); the workflow SSHs to EC2, pulls the repo, rebuilds the image, and restarts the container.

---

## Quick reference

| Item | Value |
|------|--------|
| App port in container | 8000 |
| Health (liveness) | `GET /health` |
| Readiness | `GET /health/ready` |
| Default API prefix | `/api/v1` and `/api` |
| Frontend (same container) | Served at `/` when `frontend/dist` exists in image |
