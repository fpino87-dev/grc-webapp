# Changelog

All notable changes to this project will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) — versioning: [SemVer](https://semver.org/).

---

## [Unreleased]

### Added
- Compliance Schedule: task Celery notturno `check_schedule_deadlines` (02:30) che crea automaticamente task in M08 per ogni attività in scadenza (urgency red/yellow) su tutti i plant attivi, con dedup su `source_id` e assegnazione per ruolo in base alla categoria

---

## [0.1.0] - 2026-04-10

First public release. All 21 modules (M00–M20) implemented and operational.

### Added
- M00 Governance & Organigramma — organizational structure, roles (CISO/DPO/Plant Manager), multi-plant org chart
- M01 Plant Registry — plant registry, Business Unit, NIS2 entity profile, sub-plant
- M02 RBAC — dynamic role assignment per plant, access expiry, external auditor token
- M03 Controls Library — normative controls catalog from JSON (ISO 27001, NIS2, TISAX L2/L3), gap analysis, per-plant status
- M04 Asset Inventory IT/OT — asset inventory with criticality 1–5, badge tooltips, Approved Software List (NIS2/TISAX), change management
- M05 BIA & ROI — Business Impact Analysis, RTO/RPO calculation, ALE translation
- M06 Risk Assessment IT/OT — 5×5 heat map, IEC 62443 OT score, risk treatment, formal acceptance tracking with expiry and renewal
- M07 Documents & Evidence — SHA-256 versioning, 3-level approval workflow, evidence expiry, MIME check, multi-plant sharing without re-upload
- M08 Task & Schedule — role-based assignment, expiry notifications, cross-module compliance_schedule
- M09 Incident Management — NIS2 timers (24h/72h/30d), ACN template, real-time countdown, NIS2 Art.21 classification, Excel export
- M10 Audit Trail — append-only SHA-256 hash chain, PostgreSQL trigger (no UPDATE/DELETE), `verify_audit_trail_integrity` command, annual partitioning
- M11 PDCA Controller — Plan-Do-Check-Act cycle, automatic triggers, maturity history, blocked PDCA notification
- M12 Lesson Learned & KB — knowledge base with full-text search, categorization, PDCA linkage
- M13 Management Review — minutes, attendance, action items, KPI linkage (M18)
- M14 Supplier Management — supplier registry, VDA ISA 5.x assessment, NIS2 supply chain questionnaires
- M15 Training & Awareness — training plans, KnowBe4 bidirectional integration, completion tracking, phishing campaigns
- M16 Business Continuity — BCP plans, DR tests, plan expiry, BIA linkage (M05)
- M17 Audit Preparation — TISAX/ISO/NIS2 audit readiness, findings, evidence pack, soft-delete with annul (requires all findings closed)
- M18 Reporting & Dashboard — weekly KPI snapshot, report export, cross-module dashboard, Risk/BIA/BCP tabs with heatmap and NIS2 breakdown
- M19 Notifications & Integrations — in-app notifications, email digest, SIEM webhook, per-role notification profiles
- M20 AI Engine (optional) — severity classification, RCA analysis, document drafts, anomaly detection — GDPR sanitization layer, human-in-the-loop
- Multi-language UI: IT / EN / FR / PL / TR across all modules, emails, and exports
- Multi-plant architecture with Business Unit hierarchy and per-plant NIS2 profile
- Automatic nightly backup task (02:00, 30-day retention) via Celery Beat
- Sentry integration for error monitoring — backend (Django + Celery) and frontend (React + BrowserTracing + SessionReplay), GDPR-safe
- `ModuleHelp` contextual help drawer on all main operational modules
- Bottom bar with user manual, technical manual, and donation link
- Production Docker setup: `Dockerfile.prod` + `docker-compose.prod.yml` with non-root user and Gunicorn

### Security
- JWT 30min access / 7-day refresh with rotation and blacklist (SimpleJWT + token_blacklist)
- Login rate limiting: 5/min (LoginRateThrottle); authenticated users 500/h; anonymous 20/h
- File upload: extension whitelist + real MIME check (python-magic)
- SMTP credentials encrypted at rest with Fernet AES-256 (`FERNET_KEY`)
- Password policy: minimum 12 characters, CommonPassword, NumericPassword, UserAttributeSimilarity validators
- GDPR: `anonymize_user()` in `auth_grc/services.py`, automatic monthly audit log retention
- Security HTTP headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options

### Fixed
- Resolved N+1 query patterns across controls, risk, documents, and evidence endpoints
- Fixed off-by-one date display on mitigation plans and appetite policy
- Fixed false "expired" status on formal risk acceptance created on the same day
- Fixed 500 error on risk export with missing context
- Fixed UUID serialization in management review snapshot
- Fixed Polish quotation marks in `pl/common.json` i18n files
- Fixed rate-limit 429 errors caused by mass refetch on window focus

### Changed
- Controls nightly task now uses `check_evidence_requirements`; fixed null handling on expired status
- Risk acceptance: unified simple and formal acceptance flows
- Documents: alphabetical sorting by title
- Frontend: adopted React Query with stale-time tuning to reduce redundant API calls

[0.1.0]: https://github.com/fpino87-dev/grc-webapp/releases/tag/v0.1.0
