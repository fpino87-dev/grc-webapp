#!/usr/bin/env bash
# =============================================================================
#  install_grc.sh — govrico — Full Auto Install on Ubuntu 24.04 / 26.04 LTS
#  Repo: https://github.com/fpino87-dev/grc-webapp
#
#  Uso:
#    chmod +x install_grc.sh
#    sudo ./install_grc.sh
#
#  Risultato finale:
#    https://<IP_SERVER>        → Frontend React
#    https://<IP_SERVER>/api/   → Backend Django
#
#  Nota: certificato SSL self-signed → il browser mostrerà un avviso.
#        Cliccare "Avanzate > Continua" per accedere.
#
#  Menu: installa, avvia, ferma, riavvia, aggiorna, log, stato.
#  Idempotente: ogni step controlla se già eseguito e lo salta.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Colori
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[ OK ]${RESET}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
skip()    { echo -e "${YELLOW}[SKIP]${RESET}  $* — già completato"; }
error()   { echo -e "${RED}[ERR ]${RESET}  $*" >&2; exit 1; }
step()    { echo -e "\n${BOLD}━━━ $* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"; }

# ---------------------------------------------------------------------------
# Configurazione
# ---------------------------------------------------------------------------
INSTALL_DIR="/opt/grc-webapp"
REPO_URL="https://github.com/fpino87-dev/grc-webapp.git"
NGINX_CONF_DIR="/etc/nginx/sites-available"
SSL_DIR="/etc/nginx/ssl/grc"
BACKUP_DIR="/var/backups/grc"
STATE_DIR="/var/lib/grc-install"

mkdir -p "${STATE_DIR}"
state_done()  { touch "${STATE_DIR}/$1.done"; }
state_check() { [[ -f "${STATE_DIR}/$1.done" ]]; }

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
echo -e "\n${BOLD}${CYAN}"
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║   govrico — Manager v2.4                             ║"
echo "  ║   Ubuntu LTS · Docker · Nginx SSL (self-signed)     ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo -e "${RESET}\n"

# ---------------------------------------------------------------------------
# Prerequisiti
# ---------------------------------------------------------------------------
[[ $EUID -ne 0 ]] && error "Eseguire come root: sudo ./install_grc.sh"

SERVER_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1)
[[ -z "${SERVER_IP}" ]] && SERVER_IP=$(hostname -I | awk '{print $1}')
[[ -z "${SERVER_IP}" ]] && error "Impossibile rilevare l'IP del server"
info "IP del server rilevato: ${SERVER_IP}"

# ---------------------------------------------------------------------------
# Menu principale
# ---------------------------------------------------------------------------
IS_INSTALLED=false
[[ -d "${INSTALL_DIR}/.git" ]] && IS_INSTALLED=true

echo ""
echo -e "${BOLD}  Seleziona operazione:${RESET}"
echo ""
if [[ "${IS_INSTALLED}" == "false" ]]; then
  echo -e "  ${BOLD}${GREEN}1)${RESET} Installazione completa"
  echo -e "  ${BOLD}${RED}2)${RESET} Esci"
  echo ""
  echo -ne "  Scelta [1-2]: "
  read -r MENU_CHOICE </dev/tty
  case "${MENU_CHOICE}" in
    1) info "Avvio installazione completa..." ;;
    *) echo "Uscita."; exit 0 ;;
  esac
  ACTION="install"
else
  # Leggi stato stack
  STACK_RUNNING=false
  docker compose -f "${INSTALL_DIR}/docker-compose.prod.yml"     -f "${INSTALL_DIR}/docker-compose.override.yml"     --env-file "${INSTALL_DIR}/.env.prod" ps --status running 2>/dev/null | grep -q "backend" && STACK_RUNNING=true

  echo -e "  ${BOLD}${GREEN}1)${RESET} Installazione completa (reinstalla da zero)"
  echo -e "  ${BOLD}${CYAN}2)${RESET} Restart servizi"
  echo -e "  ${BOLD}${CYAN}3)${RESET} Stop servizi"
  echo -e "  ${BOLD}${CYAN}4)${RESET} Start servizi"
  echo -e "  ${BOLD}${YELLOW}5)${RESET} Aggiornamento (git pull + rebuild + restart)"
  echo -e "  ${BOLD}${CYAN}6)${RESET} Stato servizi"
  echo -e "  ${BOLD}${CYAN}7)${RESET} Log in tempo reale"
  echo -e "  ${BOLD}${RED}8)${RESET} Esci"
  echo ""
  echo -ne "  Scelta [1-8]: "
  read -r MENU_CHOICE </dev/tty
  case "${MENU_CHOICE}" in
    1) ACTION="install" ;;
    2) ACTION="restart" ;;
    3) ACTION="stop" ;;
    4) ACTION="start" ;;
    5) ACTION="update" ;;
    6) ACTION="status" ;;
    7) ACTION="logs" ;;
    *) echo "Uscita."; exit 0 ;;
  esac
fi

# ---------------------------------------------------------------------------
# Funzioni comuni a installazione e aggiornamento
# ---------------------------------------------------------------------------
COMPOSE="docker compose -f ${INSTALL_DIR}/docker-compose.prod.yml -f ${INSTALL_DIR}/docker-compose.override.yml --env-file ${INSTALL_DIR}/.env.prod"
MEDIA_DIR="/srv/grc/media"   # bind mount di docker-compose.prod.yml (backend + celery)

# File tracciati da git che le versioni ≤ 2.3 di questo script modificavano
# (FIX A–D). Le correzioni sono ora nel repository: le modifiche locali vanno
# annullate, altrimenti `git pull --ff-only` si blocca quando upstream li cambia.
LEGACY_PATCHED_FILES=(
  docker-compose.prod.yml
  backend/Dockerfile.prod
  backend/core/settings/prod.py
  frontend/nginx.conf
)

restore_legacy_patches() {
  local f changed=()
  for f in "${LEGACY_PATCHED_FILES[@]}"; do
    git -C "${INSTALL_DIR}" diff --quiet -- "${f}" 2>/dev/null || changed+=("${f}")
  done
  if [[ ${#changed[@]} -gt 0 ]]; then
    info "Annullo le patch locali delle versioni precedenti dello script: ${changed[*]}"
    git -C "${INSTALL_DIR}" checkout -- "${changed[@]}"
  fi
  if ! git -C "${INSTALL_DIR}" diff --quiet; then
    git -C "${INSTALL_DIR}" status --short
    error "Modifiche locali nel repository in ${INSTALL_DIR}: salvale o annullale prima di aggiornare."
  fi
}

compose_supports_override_tag() {
  # `!override` nei file compose è supportato da Docker Compose 2.24.4
  local v
  v="$(docker compose version --short 2>/dev/null | sed 's/^v//')"
  [[ -n "${v}" ]] && [[ "$(printf '%s\n2.24.4\n' "${v}" | sort -V | head -1)" == "2.24.4" ]]
}

write_compose_override() {
  # backend su 127.0.0.1:8001 per nginx; frontend solo su localhost (Docker
  # pubblica le porte scavalcando UFW: con 3001:80 la SPA sarebbe raggiungibile
  # in HTTP diretto da fuori, senza passare da nginx/HTTPS).
  cat > "${INSTALL_DIR}/docker-compose.override.yml" << 'OVEREOF'
services:
  backend:
    ports:
      - "127.0.0.1:8001:8000"
OVEREOF
  if compose_supports_override_tag; then
    cat >> "${INSTALL_DIR}/docker-compose.override.yml" << 'OVEREOF'
  frontend:
    ports: !override
      - "127.0.0.1:3001:80"
OVEREOF
  else
    warn "Docker Compose < 2.24.4: il frontend resta pubblicato su 0.0.0.0:3001 — aggiorna Docker e rilancia"
  fi
  if [[ "${ENABLE_OLLAMA:-false}" == "true" ]]; then
    cat >> "${INSTALL_DIR}/docker-compose.override.yml" << 'OLLAMAEOF'
  ollama:
    image: ollama/ollama:latest
    restart: unless-stopped
    volumes:
      - ollamadata:/root/.ollama
    ports:
      - "127.0.0.1:11434:11434"

volumes:
  ollamadata:
OLLAMAEOF
  fi
}

ensure_env_defaults() {
  # Aggiunge a un .env.prod esistente le variabili introdotte dopo la sua
  # generazione e allinea la versione applicativa al file VERSION.
  local env_file="${INSTALL_DIR}/.env.prod" version
  version="$(tr -d '[:space:]' < "${INSTALL_DIR}/VERSION" 2>/dev/null || echo unknown)"
  sed -i -E "s/^APP_VERSION=.*/APP_VERSION=${version}/; s/^VITE_APP_VERSION=.*/VITE_APP_VERSION=${version}/" "${env_file}"
  if ! grep -q "^BACKUP_ENCRYPTION_KEY=." "${env_file}"; then
    local key
    key="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    sed -i '/^BACKUP_ENCRYPTION_KEY=/d' "${env_file}"
    printf '\n# Cifratura dei backup (aggiunta da install_grc.sh) — CONSERVARE: senza, i backup cifrati non si ripristinano\nBACKUP_ENCRYPTION_KEY=%s\n' "${key}" >> "${env_file}"
    [[ -f /root/grc_credentials.txt ]] && printf 'BACKUP_ENCRYPTION_KEY : %s\n' "${key}" >> /root/grc_credentials.txt
    warn "Generata BACKUP_ENCRYPTION_KEY (salvata in .env.prod e /root/grc_credentials.txt): conservala fuori dal server"
  fi
  grep -q "^DRF_NUM_PROXIES=" "${env_file}" || printf '\n# Un reverse proxy (nginx) davanti a Django\nDRF_NUM_PROXIES=1\n' >> "${env_file}"
}

prepare_media_dir() {
  mkdir -p "${MEDIA_DIR}"
}

fix_volume_permissions() {
  # Il backend gira come utente non-root `grc`: la cartella media sull'host
  # nasce di root e il volume dei backup va reso scrivibile.
  ${COMPOSE} exec -T --user root backend chown -R grc:grc /app/media /app/backups \
    || warn "chown di /app/media e /app/backups non riuscito: upload e backup potrebbero fallire"
}

load_reference_data() {
  # Tutti idempotenti: creano ciò che manca senza toccare le personalizzazioni.
  local cmd
  for cmd in load_frameworks load_notification_profiles load_competency_requirements \
             load_role_requirements load_required_documents load_training_evidence_controls \
             schedule_backup_task; do
    info "  ${cmd}"
    ${COMPOSE} exec -T backend python manage.py "${cmd}" >/dev/null \
      || warn "${cmd} non riuscito — rilanciarlo a mano"
  done
}

wait_backend() {
  local wait=0
  info "Attendo disponibilità backend..."
  until curl -sf http://127.0.0.1:8001/api/health/ &>/dev/null; do
    sleep 5; wait=$((wait+5)); echo -n "."
    [[ ${wait} -ge 180 ]] && { echo ""; warn "Timeout — verifico comunque..."; break; }
  done
  echo ""
}

# ---------------------------------------------------------------------------
# Azioni di gestione (non-install)
# ---------------------------------------------------------------------------
if [[ "${ACTION}" == "restart" ]]; then
  step "Restart servizi"
  ${COMPOSE} restart
  success "Servizi riavviati"
  ${COMPOSE} ps
  exit 0
fi

if [[ "${ACTION}" == "stop" ]]; then
  step "Stop servizi"
  ${COMPOSE} down
  success "Servizi fermati"
  exit 0
fi

if [[ "${ACTION}" == "start" ]]; then
  step "Start servizi"
  ${COMPOSE} up -d
  success "Servizi avviati"
  ${COMPOSE} ps
  exit 0
fi

if [[ "${ACTION}" == "status" ]]; then
  step "Stato servizi"
  ${COMPOSE} ps
  echo ""
  echo -e "${BOLD}  Utilizzo disco:${RESET}"
  df -h / | tail -1
  echo ""
  echo -e "${BOLD}  Utilizzo RAM:${RESET}"
  free -h | grep Mem
  exit 0
fi

if [[ "${ACTION}" == "logs" ]]; then
  step "Log in tempo reale (Ctrl+C per uscire)"
  ${COMPOSE} logs -f --tail=50
  exit 0
fi

if [[ "${ACTION}" == "update" ]]; then
  step "Aggiornamento govrico"
  cd "${INSTALL_DIR}"
  [[ -f "${STATE_DIR}/ai_choice.conf" ]] && source "${STATE_DIR}/ai_choice.conf"

  # 1. Backup completo (DB + media) con il codice attualmente in esercizio
  if ${COMPOSE} ps --status running 2>/dev/null | grep -q backend; then
    info "Backup completo prima dell'aggiornamento..."
    ${COMPOSE} exec -T backend python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.backups.services import create_backup
u = get_user_model().objects.filter(is_superuser=True, is_active=True).order_by('date_joined').first()
r = create_backup(u, backup_type='manual')
print('Backup:', r.filename, r.status)
" || error "Backup non riuscito: aggiornamento interrotto. Verificare lo spazio disco e i log del backend."
    success "Backup creato (Impostazioni → Backup)"
  else
    warn "Stack non in esecuzione: backup pre-aggiornamento saltato"
  fi

  # 2. Codice
  restore_legacy_patches
  info "Git pull..."
  git pull --ff-only
  success "Codice aggiornato alla versione $(cat VERSION 2>/dev/null || echo '?')"

  ensure_env_defaults
  write_compose_override
  prepare_media_dir

  # 3. Immagini
  info "Rebuild immagini Docker..."
  ${COMPOSE} build

  # 4. Anteprima delle migrazioni di dati (nuovo codice, database non ancora migrato)
  info "Anteprima delle migrazioni dei dati..."
  ${COMPOSE} run --rm --no-deps backend python manage.py check_training_migration_readiness 2>/dev/null \
    || info "Nessuna anteprima disponibile per questa versione"
  echo ""
  echo -ne "  Procedere con migrazioni e riavvio? Leggi prima le note di aggiornamento nel CHANGELOG [s/N] "
  read -r GO_ANSWER </dev/tty
  [[ "${GO_ANSWER,,}" == "s" ]] || error "Aggiornamento interrotto prima delle migrazioni: il codice è aggiornato ma i container girano ancora con le immagini precedenti."

  # 5. Riavvio, migrazioni, dati di riferimento
  info "Restart stack..."
  ${COMPOSE} up -d
  wait_backend

  info "Migrazioni database..."
  ${COMPOSE} exec -T backend python manage.py migrate --noinput

  fix_volume_permissions
  info "Dati di riferimento (idempotenti)..."
  load_reference_data

  success "Aggiornamento completato"
  ${COMPOSE} ps
  exit 0
fi

# ACTION == install → continua con il flusso normale sotto

# ---------------------------------------------------------------------------
# Rilevamento hardware per AI locale
# ---------------------------------------------------------------------------
RAM_GB=$(awk '/MemTotal/ {printf "%d", $2/1024/1024}' /proc/meminfo)
HAS_NVIDIA=false
HAS_AMD=false
command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null && HAS_NVIDIA=true
[[ -d /dev/dri ]] && ls /dev/dri/render* &>/dev/null && HAS_AMD=true

info "Hardware rilevato: RAM=${RAM_GB}GB | GPU NVIDIA=${HAS_NVIDIA} | GPU AMD=${HAS_AMD}"

# Scelta modello ottimale in base a RAM e GPU
choose_ollama_model() {
  if [[ "${HAS_NVIDIA}" == "true" ]] || [[ "${HAS_AMD}" == "true" ]]; then
    # Con GPU
    if   [[ ${RAM_GB} -ge 32 ]]; then echo "llama3.1:8b"
    elif [[ ${RAM_GB} -ge 16 ]]; then echo "llama3.2:3b"
    else                               echo "qwen2.5:1.5b"
    fi
  else
    # Solo CPU
    if   [[ ${RAM_GB} -ge 16 ]]; then echo "llama3.2:3b"
    elif [[ ${RAM_GB} -ge 8  ]]; then echo "llama3.2:3b"
    else                               echo "qwen2.5:1.5b"
    fi
  fi
}

# ---------------------------------------------------------------------------
# Domanda interattiva: dominio pubblico (opzionale, default = IP del server)
# ---------------------------------------------------------------------------
PUBLIC_DOMAIN=""

if ! state_check "step_domain_choice"; then
  echo ""
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${BOLD} Dominio pubblico${RESET}"
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
  echo -e "  Se la webapp sarà raggiunta tramite un nome DNS (es. ${BOLD}grc.azienda.com${RESET}),"
  echo -e "  inseriscilo qui: verrà usato in ALLOWED_HOSTS, CSRF e nel certificato."
  echo -e "  Lascia ${BOLD}vuoto${RESET} per usare l'IP del server (${BOLD}${SERVER_IP}${RESET})."
  echo ""
  echo -ne "  Dominio [invio = IP ${SERVER_IP}]: "
  read -r DOMAIN_ANSWER </dev/tty
  # Normalizza: rimuovi spazi, eventuale schema e path se incollati per intero
  PUBLIC_DOMAIN="$(echo "${DOMAIN_ANSWER}" | tr -d '[:space:]')"
  PUBLIC_DOMAIN="${PUBLIC_DOMAIN#http://}"
  PUBLIC_DOMAIN="${PUBLIC_DOMAIN#https://}"
  PUBLIC_DOMAIN="${PUBLIC_DOMAIN%%/*}"
  echo "PUBLIC_DOMAIN=${PUBLIC_DOMAIN}" > "${STATE_DIR}/domain_choice.conf"
  if [[ -n "${PUBLIC_DOMAIN}" ]]; then
    success "Dominio configurato: ${PUBLIC_DOMAIN} (IP ${SERVER_IP} resta come fallback)"
  else
    info "Nessun dominio — accesso via IP ${SERVER_IP}"
  fi
  state_done "step_domain_choice"
else
  source "${STATE_DIR}/domain_choice.conf"
  skip "Scelta dominio già effettuata (${PUBLIC_DOMAIN:-IP ${SERVER_IP}})"
fi

# Derivati host/origin/cert — calcolati a ogni run da PUBLIC_DOMAIN
if [[ -n "${PUBLIC_DOMAIN}" ]]; then
  ALLOWED_HOSTS_VALUE="${PUBLIC_DOMAIN},${SERVER_IP},localhost,127.0.0.1"
  PUBLIC_ORIGIN="https://${PUBLIC_DOMAIN}"
  CSRF_VALUE="https://${PUBLIC_DOMAIN},https://${SERVER_IP}"
  CERT_CN="${PUBLIC_DOMAIN}"
  CERT_SAN="subjectAltName=DNS:${PUBLIC_DOMAIN},IP:${SERVER_IP},IP:127.0.0.1"
  CERT_LABEL="${PUBLIC_DOMAIN} (+ IP ${SERVER_IP})"
else
  ALLOWED_HOSTS_VALUE="${SERVER_IP},localhost,127.0.0.1"
  PUBLIC_ORIGIN="https://${SERVER_IP}"
  CSRF_VALUE="https://${SERVER_IP}"
  CERT_CN="${SERVER_IP}"
  CERT_SAN="subjectAltName=IP:${SERVER_IP},IP:127.0.0.1"
  CERT_LABEL="IP ${SERVER_IP}"
fi

# ---------------------------------------------------------------------------
# Domanda interattiva: abilitare AI locale?
# ---------------------------------------------------------------------------
ENABLE_OLLAMA=false
OLLAMA_MODEL=""

if ! state_check "step_ai_choice"; then
  SUGGESTED_MODEL=$(choose_ollama_model)
  echo ""
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${BOLD} Motore AI locale (Ollama)${RESET}"
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo ""
  echo -e "  Server rilevato: ${BOLD}${RAM_GB}GB RAM${RESET} | GPU NVIDIA: ${HAS_NVIDIA} | GPU AMD: ${HAS_AMD}"
  echo ""
  if [[ "${HAS_NVIDIA}" == "true" ]] || [[ "${HAS_AMD}" == "true" ]]; then
    echo -e "  ${GREEN}GPU rilevata${RESET} — AI locale consigliato"
  elif [[ ${RAM_GB} -ge 8 ]]; then
    echo -e "  ${YELLOW}Solo CPU, ${RAM_GB}GB RAM${RESET} — AI locale funziona ma sarà lento"
  else
    echo -e "  ${RED}RAM insufficiente (${RAM_GB}GB)${RESET} — AI locale sconsigliato"
  fi
  echo -e "  Modello consigliato: ${BOLD}${CYAN}${SUGGESTED_MODEL}${RESET}"
  echo ""
  echo -ne "  Vuoi installare e abilitare il motore AI locale? [s/N] "
  read -r AI_ANSWER </dev/tty
  if [[ "${AI_ANSWER,,}" == "s" ]]; then
    ENABLE_OLLAMA=true
    OLLAMA_MODEL="${SUGGESTED_MODEL}"
    echo "ENABLE_OLLAMA=true"             > "${STATE_DIR}/ai_choice.conf"
    echo "OLLAMA_MODEL=${OLLAMA_MODEL}"  >> "${STATE_DIR}/ai_choice.conf"
    success "AI locale abilitato — modello: ${OLLAMA_MODEL}"
  else
    ENABLE_OLLAMA=false
    OLLAMA_MODEL="llama3.2:3b"
    echo "ENABLE_OLLAMA=false"           > "${STATE_DIR}/ai_choice.conf"
    echo "OLLAMA_MODEL=${OLLAMA_MODEL}"  >> "${STATE_DIR}/ai_choice.conf"
    info "AI locale disabilitato — potrai abilitarlo manualmente in seguito"
  fi
  state_done "step_ai_choice"
else
  source "${STATE_DIR}/ai_choice.conf"
  skip "Scelta AI già effettuata (ENABLE_OLLAMA=${ENABLE_OLLAMA}, MODEL=${OLLAMA_MODEL})"
fi

# ---------------------------------------------------------------------------
# STEP 1 — Aggiornamento sistema
# ---------------------------------------------------------------------------
step "1/9 · Aggiornamento sistema"

if state_check "step1_sysupdate"; then
  skip "Aggiornamento sistema"
else
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get upgrade -y -qq 2>/dev/null
  state_done "step1_sysupdate"
  success "Sistema aggiornato"
fi

# ---------------------------------------------------------------------------
# STEP 2 — Dipendenze
# ---------------------------------------------------------------------------
step "2/9 · Installazione dipendenze"

if state_check "step2_deps"; then
  skip "Dipendenze di sistema"
else
  export DEBIAN_FRONTEND=noninteractive
  apt-get install -y -qq \
    curl wget git ca-certificates gnupg lsb-release \
    python3 python3-cryptography \
    nginx openssl \
    ufw fail2ban
  state_done "step2_deps"
  success "Dipendenze installate"
fi

# ---------------------------------------------------------------------------
# STEP 3 — Docker Engine + Compose v2
# ---------------------------------------------------------------------------
step "3/9 · Installazione Docker"

if command -v docker &>/dev/null; then
  skip "Docker già presente: $(docker --version)"
else
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq \
    docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  success "Docker installato"
fi

docker compose version &>/dev/null || error "Docker Compose v2 non disponibile"

# ---------------------------------------------------------------------------
# STEP 4 — Clone repository + patch sorgenti
# ---------------------------------------------------------------------------
step "4/9 · Clone repository"

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  info "Repository già presente → git pull"
  restore_legacy_patches
  git -C "${INSTALL_DIR}" pull --ff-only
else
  git clone "${REPO_URL}" "${INSTALL_DIR}"
fi
cd "${INSTALL_DIR}"
success "Repository in ${INSTALL_DIR}"

# Nessuna patch ai sorgenti: le correzioni che le versioni ≤ 2.3 applicavano
# qui (FIX A–D) sono nel repository. Il working tree resta pulito, così
# l'aggiornamento con `git pull --ff-only` non si blocca.

# ---------------------------------------------------------------------------
# STEP 5 — Generazione .env.prod
# ---------------------------------------------------------------------------
step "5/9 · Generazione .env.prod"

ENV_DST="${INSTALL_DIR}/.env.prod"

if [[ -f "${ENV_DST}" ]]; then
  warn ".env.prod già esistente — mantengo il file attuale"
else
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
  DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(20))")
  REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_hex(16))")
  ADMIN_URL=$(python3 -c "import uuid; print(str(uuid.uuid4()) + '/')")
  BACKUP_ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
  APP_VERSION_VALUE=$(tr -d '[:space:]' < "${INSTALL_DIR}/VERSION" 2>/dev/null || echo unknown)
  AI_ENGINE_VALUE="false"
  [[ "${ENABLE_OLLAMA}" == "true" ]] && AI_ENGINE_VALUE="true"

  cat > "${ENV_DST}" << ENV_CONTENT
# =============================================================================
# govrico — PRODUCTION — generato automaticamente da install_grc.sh
# IP server: ${SERVER_IP}
# =============================================================================

# --- Django ------------------------------------------------------------------
SECRET_KEY=${SECRET_KEY}
DEBUG=false
ALLOWED_HOSTS=${ALLOWED_HOSTS_VALUE}
FRONTEND_URL=${PUBLIC_ORIGIN}
DJANGO_SETTINGS_MODULE=core.settings.prod
CSRF_TRUSTED_ORIGINS=${CSRF_VALUE}
ADMIN_URL=${ADMIN_URL}
SHOW_API_DOCS=false
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
# Un reverse proxy (nginx sull'host) davanti a Django: IP reale del client da X-Forwarded-For
DRF_NUM_PROXIES=1

# --- PostgreSQL ---------------------------------------------------------------
DATABASE_URL=postgresql://grc:${DB_PASSWORD}@db:5432/grc_prod
POSTGRES_DB=grc_prod
POSTGRES_USER=grc
POSTGRES_PASSWORD=${DB_PASSWORD}

# --- Redis -------------------------------------------------------------------
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
REDIS_PASSWORD=${REDIS_PASSWORD}

# --- Fernet ------------------------------------------------------------------
FERNET_KEY=${FERNET_KEY}

# --- Email (configura con le tue credenziali SMTP) ---------------------------
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=govrico <noreply@example.com>

# --- Celery ------------------------------------------------------------------
CELERY_CONCURRENCY=4

# --- Backup ------------------------------------------------------------------
# Archivi DB + file caricati, backup automatico ogni notte alle 02:00.
# BACKUP_ENCRYPTION_KEY cifra gli archivi: CONSERVARLA fuori dal server,
# senza non si ripristinano. Deve restare distinta da FERNET_KEY.
BACKUP_DIR=/app/backups
BACKUP_ENCRYPTION_KEY=${BACKUP_ENCRYPTION_KEY}

# --- Storage -----------------------------------------------------------------
STORAGE_BACKEND=local

# --- AI Engine ---------------------------------------------------------------
# Provider cloud, chiavi e routing per funzione si configurano dall'app
# (Impostazioni → AI Engine). Qui solo il motore locale opzionale.
AI_ENGINE_ENABLED=${AI_ENGINE_VALUE}
AI_LOCAL_ENDPOINT=http://ollama:11434
AI_LOCAL_MODEL=${OLLAMA_MODEL}

# --- Reporting: ingest KPI da sistemi esterni (opzionale) ---------------------
KPI_INGEST_API_KEY=

# --- Sentry (disabilitato) ---------------------------------------------------
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.0
APP_VERSION=${APP_VERSION_VALUE}

# --- Frontend build args -----------------------------------------------------
VITE_API_URL=
VITE_SENTRY_DSN=
VITE_SENTRY_ENVIRONMENT=production
VITE_SENTRY_TRACES_RATE=0.1
VITE_SENTRY_REPLAY_ENABLED=false
VITE_SENTRY_REPLAY_SESSION_RATE=0.1
VITE_SENTRY_REPLAY_ERROR_RATE=1.0
VITE_APP_VERSION=${APP_VERSION_VALUE}
ENV_CONTENT

  chmod 600 "${ENV_DST}"
  success ".env.prod generato"

  CREDS_FILE="/root/grc_credentials.txt"
  cat > "${CREDS_FILE}" << CREDS
======================================================
  govrico — Credenziali di accesso
  Generato: $(date)
======================================================

IP Server        : ${SERVER_IP}
URL Piattaforma  : ${PUBLIC_ORIGIN}
URL Admin Django : ${PUBLIC_ORIGIN}/${ADMIN_URL}

--- Secrets (NON CONDIVIDERE MAI) ---
SECRET_KEY       : ${SECRET_KEY}
FERNET_KEY       : ${FERNET_KEY}
DB_PASSWORD      : ${DB_PASSWORD}
REDIS_PASSWORD   : ${REDIS_PASSWORD}
ADMIN_URL path   : ${ADMIN_URL}
BACKUP_ENCRYPTION_KEY : ${BACKUP_ENCRYPTION_KEY}
  (senza questa chiave i backup cifrati non si ripristinano: copiala fuori dal server)

--- AI locale ---
Abilitato        : ${AI_ENGINE_VALUE}
Modello          : ${OLLAMA_MODEL}

======================================================
CREDS
  chmod 600 "${CREDS_FILE}"
  success "Credenziali salvate in ${CREDS_FILE}"
fi

# .env.prod già esistente (reinstallazione): variabili nuove + versione
ensure_env_defaults

# ---------------------------------------------------------------------------
# STEP 6 — Certificato SSL self-signed
# ---------------------------------------------------------------------------
step "6/9 · Certificato SSL self-signed"

if [[ -f "${SSL_DIR}/grc.crt" && -f "${SSL_DIR}/grc.key" ]]; then
  skip "Certificato SSL già presente"
else
  mkdir -p "${SSL_DIR}"
  openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout "${SSL_DIR}/grc.key" \
    -out    "${SSL_DIR}/grc.crt" \
    -subj   "/C=IT/ST=Italy/L=Local/O=GRC/OU=IT/CN=${CERT_CN}" \
    -addext "${CERT_SAN}" \
    2>/dev/null
  chmod 600 "${SSL_DIR}/grc.key"
  chmod 644 "${SSL_DIR}/grc.crt"
  success "Certificato self-signed per ${CERT_LABEL} (valido 10 anni)"
fi

if [[ ! -f /etc/nginx/ssl/dhparam.pem ]]; then
  info "Generazione DH parameters (~30s)..."
  mkdir -p /etc/nginx/ssl
  openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048 2>/dev/null
  success "DH parameters generati"
else
  skip "DH parameters già presenti"
fi

# ---------------------------------------------------------------------------
# STEP 7 — Nginx reverse proxy
# ---------------------------------------------------------------------------
step "7/9 · Nginx reverse proxy"

if state_check "step7_nginx"; then
  skip "Nginx già configurato"
else
  rm -f /etc/nginx/sites-enabled/default

  # Leggi ADMIN_URL dall'env per inserirlo nella config nginx
  ADMIN_URL_NGINX=$(grep "^ADMIN_URL=" "${ENV_DST}" | cut -d= -f2)

  cat > "${NGINX_CONF_DIR}/grc" << NGINXEOF
# ── HTTP → HTTPS redirect ────────────────────────────────────────────────────
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    return 301 https://\$host\$request_uri;
}

# ── HTTPS main — Frontend React + Backend Django ─────────────────────────────
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;

    ssl_certificate      /etc/nginx/ssl/grc/grc.crt;
    ssl_certificate_key  /etc/nginx/ssl/grc/grc.key;
    ssl_dhparam          /etc/nginx/ssl/dhparam.pem;
    ssl_protocols        TLSv1.2 TLSv1.3;
    ssl_ciphers          HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache    shared:SSL:10m;
    ssl_session_timeout  10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options           "SAMEORIGIN"                          always;
    add_header X-Content-Type-Options    "nosniff"                             always;
    add_header X-XSS-Protection          "1; mode=block"                       always;
    add_header Referrer-Policy           "strict-origin-when-cross-origin"     always;

    client_max_body_size 50M;
    proxy_read_timeout   120s;
    proxy_connect_timeout 60s;

    # ── Django Admin (path UUID da ADMIN_URL) ─────────────────────────────────
    location /${ADMIN_URL_NGINX} {
        proxy_pass              http://127.0.0.1:8001;
        proxy_http_version      1.1;
        proxy_set_header        Host              \$host;
        proxy_set_header        X-Real-IP         \$remote_addr;
        proxy_set_header        X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header        X-Forwarded-Proto https;
        proxy_hide_header       X-Frame-Options;
    }

    # ── Django account (login 2FA per admin) ─────────────────────────────────
    location /account/ {
        proxy_pass              http://127.0.0.1:8001;
        proxy_http_version      1.1;
        proxy_set_header        Host              \$host;
        proxy_set_header        X-Real-IP         \$remote_addr;
        proxy_set_header        X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header        X-Forwarded-Proto https;
        proxy_hide_header       X-Frame-Options;
    }

    # ── Django REST API ───────────────────────────────────────────────────────
    location /api/ {
        proxy_pass              http://127.0.0.1:8001;
        proxy_http_version      1.1;
        proxy_set_header        Host              \$host;
        proxy_set_header        X-Real-IP         \$remote_addr;
        proxy_set_header        X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header        X-Forwarded-Proto https;
        proxy_hide_header       X-Frame-Options;
    }

    # ── Static / Media Django ─────────────────────────────────────────────────
    location /static/ {
        proxy_pass         http://127.0.0.1:8001;
        proxy_set_header   X-Forwarded-Proto https;
    }
    location /media/ {
        proxy_pass         http://127.0.0.1:8001;
        proxy_set_header   X-Forwarded-Proto https;
    }

    # ── Frontend React SPA ────────────────────────────────────────────────────
    location / {
        proxy_pass              http://127.0.0.1:3001;
        proxy_http_version      1.1;
        proxy_set_header        Host              \$host;
        proxy_set_header        X-Real-IP         \$remote_addr;
        proxy_set_header        X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header        X-Forwarded-Proto https;
        proxy_set_header        Upgrade           \$http_upgrade;
        proxy_set_header        Connection        "upgrade";
        proxy_hide_header       X-Frame-Options;
        proxy_hide_header       Content-Security-Policy;
        proxy_hide_header       Referrer-Policy;
        proxy_hide_header       Permissions-Policy;
        proxy_hide_header       X-Content-Type-Options;
        proxy_buffering         off;
    }
}
NGINXEOF

  ln -sf "${NGINX_CONF_DIR}/grc" /etc/nginx/sites-enabled/grc
  nginx -t 2>/dev/null && systemctl restart nginx && systemctl enable nginx
  state_done "step7_nginx"
  success "Nginx configurato (80 → 443)"
fi

# ---------------------------------------------------------------------------
# STEP 8 — Firewall UFW
# ---------------------------------------------------------------------------
step "8/9 · Firewall UFW"

if state_check "step8_ufw"; then
  skip "Firewall già configurato"
else
  # Server dedicato: le regole UFW esistenti vengono sostituite.
  if ufw status 2>/dev/null | grep -q "Status: active"; then
    warn "UFW già attivo: le regole attuali vengono azzerate e sostituite (22, 80, 443)"
  fi
  ufw --force reset
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow ssh
  ufw allow 80/tcp   comment "HTTP redirect"
  ufw allow 443/tcp  comment "HTTPS GRC"
  ufw --force enable
  state_done "step8_ufw"
  success "Firewall: 22·80·443 aperte"
fi

# ---------------------------------------------------------------------------
# STEP 9 — Build stack Docker, migrazioni, seed, superuser
# ---------------------------------------------------------------------------
step "9/9 · Build e avvio stack Docker"

cd "${INSTALL_DIR}"

# Override: backend su 127.0.0.1:8001 e frontend su 127.0.0.1:3001 per nginx,
# ollama se abilitato
write_compose_override
prepare_media_dir

info "Build Docker (prima esecuzione: 5-15 min, le successive usano cache)..."
${COMPOSE} build

info "Avvio stack..."
${COMPOSE} up -d
success "Stack avviato"

wait_backend

EXEC="docker compose -f docker-compose.prod.yml -f docker-compose.override.yml --env-file .env.prod exec -T backend"

info "Migrazioni database..."
${EXEC} python manage.py migrate --noinput
success "Migrazioni OK"

# Permessi: cartella media sull'host e volume backup scrivibili dall'utente grc
info "Permessi /app/media e /app/backups..."
fix_volume_permissions
success "Permessi OK"

info "Dati di riferimento (framework, profili notifica, competenze, requisiti, backup notturno)..."
load_reference_data
success "Dati di riferimento caricati (ISO 27001, NIS2, ACN NIS2, TISAX) e backup automatico programmato alle 02:00"

# Policy di workflow documentale predefinite: solo alla prima installazione,
# perché il comando aggiorna anche le policy di organizzazione già presenti.
if state_check "step9_workflow_policies"; then
  skip "Policy di workflow documentale"
else
  ${EXEC} python manage.py load_document_workflow_policies \
    && state_done "step9_workflow_policies" \
    || warn "load_document_workflow_policies non riuscito — rilanciarlo a mano"
fi

info "Check deploy Django..."
${EXEC} python manage.py check --deploy 2>&1 | grep -vE "^(System check|$)" || true

# ---------------------------------------------------------------------------
# Configurazione AI nel DB (get_or_create con modello scelto dall'utente)
# ---------------------------------------------------------------------------
if [[ "${ENABLE_OLLAMA}" == "true" ]]; then
  info "Configurazione AI locale nel database (modello: ${OLLAMA_MODEL})..."
  ${EXEC} python manage.py shell -c "
from apps.ai_engine.models import AiProviderConfig
routing = {'chatbot':'ollama','rca_draft':'ollama','gap_actions':'ollama','review_summary':'ollama'}
c, created = AiProviderConfig.objects.get_or_create(
    defaults={
        'name': 'Configurazione AI principale',
        'active': True,
        'local_endpoint': 'http://ollama:11434',
        'local_model': '${OLLAMA_MODEL}',
        'task_routing': routing,
    }
)
if not created:
    c.local_endpoint = 'http://ollama:11434'
    c.local_model = '${OLLAMA_MODEL}'
    c.task_routing = routing
    c.save()
print('Config AI', 'creata' if created else 'aggiornata', '| endpoint:', c.local_endpoint, '| model:', c.local_model)
" || warn "Config AI DB non aggiornata — configurabile manualmente dalle impostazioni"

  info "Download modello Ollama: ${OLLAMA_MODEL} (può richiedere diversi minuti)..."
  OLLAMA_CONTAINER=$(docker compose -f docker-compose.prod.yml \
    -f docker-compose.override.yml --env-file .env.prod \
    ps -q ollama 2>/dev/null || true)
  if [[ -n "${OLLAMA_CONTAINER}" ]]; then
    docker exec "${OLLAMA_CONTAINER}" ollama pull "${OLLAMA_MODEL}"
    success "Modello ${OLLAMA_MODEL} scaricato"
  else
    warn "Container ollama non trovato — scarica il modello manualmente:"
    warn "  docker exec grc-webapp-ollama-1 ollama pull ${OLLAMA_MODEL}"
  fi
fi

# ---------------------------------------------------------------------------
# Creazione superuser
# ---------------------------------------------------------------------------
if state_check "step9_superuser"; then
  skip "Superuser già creato"
else
  echo ""
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${BOLD} Crea l'account amministratore della piattaforma GRC${RESET}"
  echo -e "${BOLD}${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
  ${COMPOSE} exec backend python manage.py createsuperuser
  state_done "step9_superuser"
  success "Superuser creato"
fi

# ---------------------------------------------------------------------------
# Systemd service — avvio automatico al boot
# ---------------------------------------------------------------------------
if state_check "step9_systemd"; then
  skip "Systemd service già configurato"
else
  cat > /etc/systemd/system/grc-webapp.service << SVCEOF
[Unit]
Description=govrico (Docker Compose)
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml -f docker-compose.override.yml --env-file .env.prod up -d
ExecStop=/usr/bin/docker compose  -f docker-compose.prod.yml -f docker-compose.override.yml --env-file .env.prod down
TimeoutStartSec=300
Restart=on-failure

[Install]
WantedBy=multi-user.target
SVCEOF
  systemctl daemon-reload
  systemctl enable grc-webapp.service
  state_done "step9_systemd"
  success "Systemd service abilitato"
fi

# ---------------------------------------------------------------------------
# Backup automatico: lo gestisce l'applicazione (Celery, ogni notte alle 02:00,
# archivio DB + file caricati, cifrato, retention 30 giorni) — programmato
# sopra da `schedule_backup_task`. Le versioni ≤ 2.3 creavano anche un cron
# sull'host con il solo dump del DB in chiaro: se presente, lo segnaliamo.
# ---------------------------------------------------------------------------
if [[ -f /etc/cron.d/grc-backup ]]; then
  warn "Trovato il vecchio cron /etc/cron.d/grc-backup (solo DB, non cifrato, in ${BACKUP_DIR})."
  warn "Il backup completo è ora nell'app: valuta di rimuoverlo con  rm /etc/cron.d/grc-backup"
fi

# ---------------------------------------------------------------------------
# Riepilogo finale
# ---------------------------------------------------------------------------
ADMIN_URL_PATH=$(grep "^ADMIN_URL=" "${ENV_DST}" | cut -d= -f2)

echo ""
echo -e "${BOLD}${GREEN}"
echo "  ╔══════════════════════════════════════════════════════════╗"
echo "  ║   ✅  Installazione completata con successo!             ║"
echo "  ╚══════════════════════════════════════════════════════════╝"
echo -e "${RESET}"
echo -e "  🌐  govrico           →  ${BOLD}${CYAN}${PUBLIC_ORIGIN}${RESET}"
echo -e "  🔧  Admin Django      →  ${BOLD}${CYAN}${PUBLIC_ORIGIN}/${ADMIN_URL_PATH}${RESET}"
echo ""
if [[ "${ENABLE_OLLAMA}" == "true" ]]; then
  echo -e "  🤖  AI locale         →  ${BOLD}${GREEN}Abilitato${RESET} · Ollama · ${OLLAMA_MODEL}"
else
  echo -e "  🤖  AI locale         →  ${YELLOW}Disabilitato${RESET} (configura provider cloud dalle impostazioni)"
fi
echo ""
echo -e "${YELLOW}${BOLD}  ⚠  SSL self-signed:${RESET} il browser mostrerà 'Connessione non sicura'."
echo -e "     Clicca ${BOLD}Avanzate → Procedi${RESET} per accedere."
echo ""
echo -e "  📋  Credenziali e secrets → ${BOLD}/root/grc_credentials.txt${RESET}"
echo -e "  🔐  Copia ${BOLD}BACKUP_ENCRYPTION_KEY${RESET} fuori dal server: senza, i backup non si ripristinano"
echo -e "  💾  Backup automatico     → ogni notte alle 02:00 (Impostazioni → Backup)"
echo -e "  📂  Stato installazione   → ${BOLD}${STATE_DIR}/${RESET}"
echo ""
echo -e "${BOLD}  Comandi utili:${RESET}"
echo -e "    cd ${INSTALL_DIR}"
echo -e "    docker compose -f docker-compose.prod.yml -f docker-compose.override.yml --env-file .env.prod logs -f"
echo -e "    docker compose -f docker-compose.prod.yml -f docker-compose.override.yml --env-file .env.prod ps"
echo -e "    systemctl restart grc-webapp"
echo -e "    sudo ./install_grc.sh   → menu: aggiornamento (backup + anteprima + migrazioni), log, stato"
echo ""
