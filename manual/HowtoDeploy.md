# How to deploy GRC Webapp on Ubuntu (production-oriented)

This guide walks through installing the stack on a **fresh Ubuntu Server** (22.04 LTS or 24.04 LTS), securing the host, running the **Docker Compose production** stack, and putting the application **online** behind a reverse proxy with TLS.

It is **generic**: replace every placeholder domain, password, and path with values appropriate to your organization.

---

## Table of contents

1. [Architecture overview](#1-architecture-overview)
2. [Server requirements](#2-server-requirements)
3. [Initial server hardening](#3-initial-server-hardening)
4. [Install Docker Engine and Compose](#4-install-docker-engine-and-compose)
5. [Firewall (UFW)](#5-firewall-ufw)
6. [Obtain the application code](#6-obtain-the-application-code)
7. [Configure environment variables](#7-configure-environment-variables)
8. [Expose services for the reverse proxy](#8-expose-services-for-the-reverse-proxy)
9. [Build and start the stack](#9-build-and-start-the-stack)
10. [Database migrations and seed data](#10-database-migrations-and-seed-data)
11. [Reverse proxy and TLS](#11-reverse-proxy-and-tls)
12. [Health checks and smoke tests](#12-health-checks-and-smoke-tests)
13. [Backups and operations](#13-backups-and-operations)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Architecture overview

Typical layout:

```
Internet → HTTPS (443) → Reverse proxy (Nginx / Nginx Proxy Manager)
                              ├─→ Frontend container (static SPA, e.g. host port 3001)
                              └─→ Backend API (Django, e.g. path /api/ → backend :8000)
```

The production compose file (`docker-compose.prod.yml`) publishes the **frontend** on host port **3001** by default. The **backend** service has **no** host port in the default file; you should bind the backend to **loopback only** so only the reverse proxy on the same host can reach it (see [section 8](#8-expose-services-for-the-reverse-proxy)).

The SPA calls the API with a **relative** base path `/api/v1` when frontend and API are served under the **same public hostname** (recommended). Set `VITE_API_URL` empty in that case.

---

## 2. Server requirements

| Resource | Minimum (small team) | Recommended |
|----------|----------------------|-------------|
| CPU | 2 vCPU | 4+ vCPU |
| RAM | 4 GB | 8 GB+ |
| Disk | 40 GB SSD | 100 GB+ SSD |
| OS | Ubuntu 22.04 / 24.04 LTS | Same |

Install **64-bit** Ubuntu Server. Use a dedicated or virtual machine; avoid sharing the host with untrusted workloads.

---

## 3. Initial server hardening

Run as a user with `sudo`.

1. **Update packages**

   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Create a non-root deploy user** (optional but recommended)

   ```bash
   sudo adduser grcdeploy
   sudo usermod -aG sudo grcdeploy
   ```

3. **SSH hardening** (summary)

   - Prefer SSH keys; disable password authentication for SSH when keys are in place.
   - Set `PermitRootLogin no` in `/etc/ssh/sshd_config` after verifying key access.
   - Restart SSH: `sudo systemctl restart ssh`

4. **Automatic security updates** (optional)

   ```bash
   sudo apt install -y unattended-upgrades
   sudo dpkg-reconfigure --priority=low unattended-upgrades
   ```

---

## 4. Install Docker Engine and Compose

Follow the official Docker documentation for Ubuntu, or use the convenience script only on trusted networks. Example using the official repository:

```bash
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Add your deploy user to the `docker` group:

```bash
sudo usermod -aG docker $USER
# Log out and back in for the group to apply
```

Verify:

```bash
docker --version
docker compose version
```

---

## 5. Firewall (UFW)

Allow SSH first, then HTTP/HTTPS, then enable the firewall.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

**Do not** expose PostgreSQL or Redis to the public internet. They must stay on the Docker internal network only.

If you use **Nginx Proxy Manager** on the same host (often published on 80/81/443), ensure only required ports are open. Restrict port **81** (NPM admin UI) to your office IP or VPN if possible.

---

## 6. Obtain the application code

```bash
cd /opt
sudo mkdir -p grc-webapp
sudo chown $USER:$USER grc-webapp
cd grc-webapp
git clone <YOUR_REPOSITORY_URL> .
```

Use a stable branch or release tag for production.

---

## 7. Configure environment variables

1. Copy the production template:

   ```bash
   cp .env.prod.example .env.prod
   ```

2. Edit `.env.prod` and set **every** value marked as required. See inline comments in `.env.prod.example` and the table below.

3. **Generate secrets** (run on your workstation or the server):

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. **Key variables** (non-exhaustive; see `.env.prod.example` for the full list):

   | Variable | Purpose |
   |----------|---------|
   | `SECRET_KEY` | Django secret; must be unique and long |
   | `FERNET_KEY` | Encrypts SMTP passwords in DB |
   | `ALLOWED_HOSTS` | Comma-separated hostnames served by Django |
   | `FRONTEND_URL` | Public HTTPS URL of the UI (used for CORS and email links) |
   | `CSRF_TRUSTED_ORIGINS` | Same origin(s) as the browser uses (HTTPS) |
   | `DATABASE_URL` | PostgreSQL URL (points to `db` service in compose) |
   | `POSTGRES_*` | Credentials for the `db` container |
   | `REDIS_URL` / `REDIS_PASSWORD` | Redis with password; must match compose |
   | `ADMIN_URL` | Non-guessable path for Django admin |
   | `VITE_*` | Frontend build-time Sentry and version (optional) |

5. **`VITE_API_URL`**: For a **single hostname** where Nginx forwards `/api` to the backend, leave **empty** so the browser uses same-origin `/api/v1`. If you split API to another host, set the full API base URL at **build time** and rebuild the frontend.

---

## 8. Expose services for the reverse proxy

The default `docker-compose.prod.yml` maps:

- **Frontend**: `3001:80` (host → container)

The **backend** must be reachable by the reverse proxy on the host. Recommended: publish **only on localhost**:

Create `docker-compose.override.yml` next to `docker-compose.prod.yml`:

```yaml
services:
  backend:
    ports:
      - "127.0.0.1:8000:8000"
```

This keeps the API off the public interface while allowing Nginx (or NPM) on the host to connect to `http://127.0.0.1:8000`.

Alternatively, attach a reverse proxy **inside** the same Docker network (advanced; not covered in detail here).

---

## 9. Build and start the stack

From the repository root (load variables for build-time `VITE_*` args):

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml build
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

Check containers:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f --tail=50 backend
```

---

## 10. Database migrations and seed data

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
docker compose -f docker-compose.prod.yml exec backend python manage.py load_frameworks
docker compose -f docker-compose.prod.yml exec backend python manage.py load_notification_profiles
docker compose -f docker-compose.prod.yml exec backend python manage.py load_competency_requirements
docker compose -f docker-compose.prod.yml exec backend python manage.py load_required_documents
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Optional: schedule backups (if your project provides a management command):

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py schedule_backup_task
```

Run `check --deploy`:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py check --deploy
```

---

## 11. Reverse proxy and TLS

### Option A — Nginx Proxy Manager (NPM)

Often run as a separate Docker stack. Create **Proxy Hosts**:

1. **Frontend**

   - Domain: `grc.example.com` (your domain)
   - Scheme: `http`
   - Forward hostname: `172.17.0.1` or host Docker bridge IP / `host.docker.internal` depending on your setup
   - Forward port: `3001`
   - Enable **Block Common Exploits**, **Websockets Support** if needed
   - SSL: request Let's Encrypt certificate; force SSL

2. **API path** (same hostname — recommended)

   - Custom location: `/api`
   - Forward to `http://127.0.0.1:8000` (or your backend socket)
   - Preserve **Host** and **X-Forwarded-Proto** headers
   - Increase `client_max_body_size` if users upload large files (e.g. `50m`)

Ensure DNS **A** record points to your server public IP.

### Option B — Native Nginx on Ubuntu

Example server block (illustrative only — adjust paths and certificates):

```nginx
server {
    listen 443 ssl http2;
    server_name grc.example.com;

    ssl_certificate     /etc/letsencrypt/live/grc.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/grc.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50m;
    }
}
```

Obtain certificates with **Certbot** (`certbot --nginx`) or DNS validation.

---

## 12. Health checks and smoke tests

```bash
curl -fsS http://127.0.0.1:8000/api/health/
curl -fsSI https://grc.example.com/
```

Log in through the browser, verify login, language switch, and a sample API call from the UI.

---

## 13. Backups and operations

- **Database**: schedule `pg_dump` from the PostgreSQL container or host (see `INFRASTRUCTURE.md` for retention ideas).
- **Uploaded files**: if `STORAGE_BACKEND=local`, include the media path in backups; if `s3`, rely on bucket versioning/replication.
- **Secrets**: store `.env.prod` outside version control; restrict file permissions (`chmod 600 .env.prod`).

---

## 14. Troubleshooting

| Symptom | Check |
|---------|--------|
| 502 from proxy | Backend not listening on expected host port; override file applied? `docker compose ps` |
| CSRF / login fails | `CSRF_TRUSTED_ORIGINS`, `FRONTEND_URL`, HTTPS headers `X-Forwarded-Proto` |
| CORS errors | `FRONTEND_URL` must match the browser origin exactly |
| Static/admin 404 | `collectstatic` runs in image build; rebuild if settings changed |
| Celery tasks not running | `celery` and `celery-beat` containers up; Redis password matches |

For deeper infrastructure notes, see [`../INFRASTRUCTURE.md`](../INFRASTRUCTURE.md).

---

## Related files

- [`.env.prod.example`](../.env.prod.example) — production variable template with comments  
- [`.env.example`](../.env.example) — local development template  
- [`../README.md`](../README.md) — project overview and quick starts  
- [`../INFRASTRUCTURE.md`](../INFRASTRUCTURE.md) — extended infrastructure reference  
