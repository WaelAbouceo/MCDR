# CI/CD: Deploy to EC2 from GitHub

Pushes to `main` (and manual runs) trigger a GitHub Actions workflow that SSHs to your EC2 instance, pulls the latest code, rebuilds the Docker image, and restarts the app.

## One-time setup

### 1. EC2 already set up

The workflow assumes on the EC2 instance you already have:

- `~/MCDR` – repo cloned (e.g. `git clone https://github.com/WaelAbouceo/MCDR.git ~/MCDR`)
- `~/MCDR/.env` – production env (SECRET_KEY, CORS_ORIGINS, DB paths, etc.)
- `~/MCDR/data/` – SQLite DBs (or run `./scripts/init_db_ec2.sh data` once)

If not, do that first (see [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)).

### 2. GitHub secrets

In your GitHub repo: **Settings → Secrets and variables → Actions → New repository secret.**

Add:

| Secret        | Description |
|---------------|-------------|
| `EC2_HOST`    | EC2 public IP or hostname, e.g. `54.93.95.137`. Use an **Elastic IP** if you want a stable address. |
| `EC2_SSH_KEY` | Full contents of your EC2 SSH private key (the `.pem` file). Copy everything including `-----BEGIN ...` and `-----END ...`. |

**Get the key contents (on your Mac):**

```bash
cat /Users/waelabouella/MCDR/Gochat247_test.pem
```

Paste that entire output into the `EC2_SSH_KEY` secret. Do not commit the `.pem` file.

### 3. SSH key on EC2 (optional)

If the key has a passphrase, `appleboy/ssh-action` may prompt. Use a **deploy key without a passphrase** for CI:

1. On your Mac: `ssh-keygen -t ed25519 -C "github-deploy" -f deploy_ec2 -N ""`
2. Add `deploy_ec2.pub` to EC2: append it to `~/.ssh/authorized_keys` for user `ubuntu`.
3. Put the **private** key contents (`deploy_ec2`) into the `EC2_SSH_KEY` secret.

Then you can keep your existing `.pem` for your own SSH and use the deploy key only for GitHub Actions.

## How it works

- **Trigger:** Push to `main`, or **Actions → Deploy to EC2 → Run workflow**.
- **Steps:** SSH to EC2 → `cd ~/MCDR` → `git fetch && git reset --hard origin/main` → `docker rm -f mcdr` → `docker build` → `docker run` (same volume and env as before).
- **Result:** New container from latest image; app at `http://EC2_HOST/`.

## Elastic IP (recommended)

Without an Elastic IP, the EC2 public IP can change after stop/start. Then you’d have to update `EC2_HOST` in GitHub secrets.

1. In AWS: **EC2 → Elastic IPs → Allocate**, then **Associate** with your instance.
2. Use that IP as `EC2_HOST` in GitHub secrets.

## Troubleshooting

| Issue | Check |
|-------|--------|
| Workflow fails at SSH | Verify `EC2_HOST` (current public IP or Elastic IP) and `EC2_SSH_KEY` (full key, no extra spaces). |
| "~/MCDR not found" | SSH to EC2 and clone the repo: `git clone https://github.com/WaelAbouceo/MCDR.git ~/MCDR`. |
| Build fails on EC2 | Look at the workflow log; fix frontend/backend build or dependencies. |
| Container exits after deploy | On EC2 run `docker logs mcdr`; fix .env or DB paths (see [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md)). |
