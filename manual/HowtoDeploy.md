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
15. [First-time application configuration](#15-first-time-application-configuration)

---

## 1. Architecture overview

Typical layout:

```
Internet → HTTPS (443) → Reverse proxy (Nginx / Nginx Proxy Manager)
                              ├─→ Frontend container (static SPA, e.g. host port 3001)
                              └─→ Backend API (Django, e.g. path /api/ → backend :8000)
```

The production compose file (`docker-compose.prod.yml`) publishes the **frontend** on host port **3001** by default. It references `backend/Dockerfile.prod` and `frontend/Dockerfile.prod` — both exist in the repository; do not look for a `Dockerfile.prod` at the root. The **backend** service has **no** host port in the default file; you should bind the backend to **loopback only** so only the reverse proxy on the same host can reach it (see [section 8](#8-expose-services-for-the-reverse-proxy)).

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

> **Important**: Docker Compose only auto-loads `docker-compose.override.yml` when using the default file name. Because all production commands use `-f docker-compose.prod.yml` explicitly, you must **always** append `-f docker-compose.override.yml` to every `docker compose` command from this point on (see section 9).

Alternatively, attach a reverse proxy **inside** the same Docker network (advanced; not covered in detail here).

---

## 9. Build and start the stack

From the repository root (load variables for build-time `VITE_*` args):

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.override.yml build
docker compose --env-file .env.prod -f docker-compose.prod.yml -f docker-compose.override.yml up -d
```

Check containers:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml ps
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml logs -f --tail=50 backend
```

---

## 10. Database migrations and seed data

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec backend python manage.py migrate
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec backend python manage.py load_frameworks
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec backend python manage.py load_notification_profiles
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec backend python manage.py load_competency_requirements
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec backend python manage.py load_required_documents
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec backend python manage.py createsuperuser
```

Optional: schedule backups (if your project provides a management command):

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec backend python manage.py schedule_backup_task
```

Run `check --deploy`:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec backend python manage.py check --deploy
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
curl -fsS http://127.0.0.1:8000/api/health/   # requires the override file applied in section 8
curl -fsSI https://grc.example.com/
```

Log in through the browser, verify login, language switch, and a sample API call from the UI.

---

## 13. Backups and operations

- **Database**: schedule `pg_dump` from the PostgreSQL container or host (see `INFRASTRUCTURE.md` for retention ideas).
- **Uploaded files**: the current build uses local filesystem storage (`STORAGE_BACKEND=local` in `.env.prod`). Include the backend media volume in your backup plan (e.g. `pg_dump` covers the database; the file store on disk must be backed up separately). S3/object storage is not yet implemented.
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

## 15. First-time application configuration

This section assumes the **containers are running**, **migrations and CLI seeds from section 10 are complete**, the app is reachable over **HTTPS**, and at least one **Django superuser** exists.

The goal is a **minimal working configuration**: users can select a site (plant), see **controls** for that site, and receive **notifications** according to your policies.

### 15.1 Sign in and baseline checks

1. Open the public URL of the application (e.g. `https://app.example.com`).
2. Sign in with the **superuser** account created via `createsuperuser`.
3. Confirm the **plant selector** (top bar) appears. If you have no plants yet, it may be empty until you create one (next steps).
4. Switch **language** (top bar) once to verify i18n loads.

### 15.2 Multi-factor authentication (MFA) — strongly recommended

1. Go to **MFA** / two-factor settings (sidebar: *MFA* / authenticator setup — path may be `/settings/mfa` depending on your build).
2. Enrol **TOTP** (authenticator app) for the superuser account.
3. Log out and log back in to confirm the MFA step works.

Repeat for other privileged accounts after they are created.

### 15.3 Outbound email (SMTP)

1. Ensure `.env.prod` already defines **SMTP** (`EMAIL_HOST`, `EMAIL_PORT`, TLS, credentials, `DEFAULT_FROM_EMAIL`).
2. As **super_admin**, open **Settings → Email** (if available in your build) and verify or complete the configuration.
3. Trigger a flow that sends mail (e.g. password reset or a notification test, if the UI provides one) and confirm delivery.

Without working SMTP, **digest and alert emails** will not be delivered (in-app notifications may still work depending on configuration).

### 15.4 Create the first site (plant)

1. Open **Sites** / **Plant registry** (sidebar, e.g. `/plants`).
2. Create a **plant**: code, name, address fields, and **NIS2 scope** (or equivalent) as required by your organisation.
3. Save. This site becomes the scope for controls, assets, risks, documents, and other modules.

### 15.5 Attach regulatory frameworks to the plant

Catalogue data was loaded by **`load_frameworks`** (section 10). You must **link** frameworks to each plant so that **control instances** are generated.

1. On the plant list, open the **frameworks** action for the new plant (or the plant detail UI where frameworks are managed).
2. **Assign** at least one framework (e.g. ISO 27001, NIS2, TISAX) with the correct **level** / options for your case.
3. On save, the application **creates control instances** for that plant and framework.

4. Open **Controls** (`/controls`), select the **plant** in the top bar, and confirm that **control rows** appear (status may be “not evaluated” initially).

If no controls appear, verify that frameworks are **active** for the plant and not archived.

### 15.6 Organisation and risk appetite (optional but typical)

1. Open **Governance** (`/governance`) and complete any **organisational** data your process requires (e.g. roles, workflow, risk appetite / thresholds if your deployment uses them).
2. Adjust **risk appetite** or compliance thresholds **per plant / framework** if your UI exposes them — this affects how risk and reporting behave later.

Exact fields depend on your GRC process; skip what your organisation does not use in phase one.

### 15.7 Users, roles, and plant access

1. Open **Users** (`/users`) — typically **super_admin** only for creation.
2. **Create** operational accounts (compliance, plant managers, etc.).
3. Assign each user a **GRC role** and **access to the relevant plant(s)** (multi-plant users need each site linked).

Without plant access, users may not see data scoped to a site.

### 15.8 Notification profiles

Default profiles were loaded by **`load_notification_profiles`** (section 10).

1. As **super_admin**, open **Settings → Notification rules** (or equivalent).
2. Review **channels** (e.g. email), **frequencies**, and **roles** targeted by each rule.
3. Tune rules so the right people receive deadlines and escalations for your organisation.

### 15.9 Backups (recommended before going live)

If you have not already run:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.override.yml exec backend python manage.py schedule_backup_task
```

schedule the **automatic backup** task according to your operations guide, and verify backup files or retention in your chosen storage.

### 15.10 Smoke test of a “ready” tenant

1. **Plant** selected in the top bar matches the site you configured.
2. **Controls** list shows instances for assigned frameworks.
3. **Dashboard** or **Reporting** loads without errors for that plant.
4. A **non–superuser** test account (with plant access) can log in and see the same plant scope.

You can then roll out further modules (assets, BIA, risk, documents, incidents) following your internal methodology.

---

## Related files

- [`.env.prod.example`](../.env.prod.example) — production variable template with comments  
- [`.env.example`](../.env.example) — local development template  
- [`../README.md`](../README.md) — project overview and quick starts  
- [`../INFRASTRUCTURE.md`](../INFRASTRUCTURE.md) — extended infrastructure reference  
