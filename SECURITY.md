# Security Policy

This document describes our **coordinated vulnerability disclosure** process, aligned with
the EU **Cyber Resilience Act** (Reg. 2024/2847, Art. 13) and **ISO/IEC 29147**.
For the broader compliance dossier (GDPR / AI Act / transfers) see [`compliance/`](compliance/README.md).
Security requests may be sent in English or Italian.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest `0.x` release on `main` | Yes |
| Older releases | Best-effort |

Only the latest release line receives security fixes. Older versions are not backported.

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use [GitHub Security Advisories](https://github.com/fpino87-dev/grc-webapp/security/advisories/new) to report vulnerabilities privately.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Affected version(s)
- Suggested fix (if any)

### Response SLA

| Event | Target |
|-------|--------|
| Acknowledge receipt | 7 days |
| Confirm or dismiss | 14 days |
| Publish fix (if confirmed) | 90 days |

After the fix is released, a CVE will be requested if the severity warrants it (CVSS >= 4.0).

---

## Scope

**In scope:**
- Authentication and authorization (JWT, RBAC, session management)
- Audit trail integrity (hash chain, PostgreSQL trigger)
- File upload validation (MIME check, path traversal)
- API endpoints (injection, IDOR, privilege escalation)
- Sensitive data exposure (credentials, PII, ALE values)
- Docker/deployment configuration (secrets leakage, non-root user)

**Out of scope:**
- Vulnerabilities requiring physical access to the server
- Denial of service attacks
- Social engineering
- Third-party dependencies not directly bundled in this repository (report upstream)

---

## Security Practices

- Dependencies are continuously scanned in CI (`.github/workflows/security-audit.yml`): `pip-audit` (backend, strict) and `npm audit` (frontend, high/critical gate)
- Security-relevant changes are tagged `security` in CHANGELOG.md
- The audit trail (M10) is append-only and cryptographically chained — tampering is detectable
- No PII reaches external AI services without passing through `Sanitizer.sanitize()` (M20); a local-LLM (Ollama) option avoids external transfer entirely
- Production deployment uses non-root Docker containers; secrets are never committed to the repository
- A **Software Bill of Materials (SBOM)** can be produced from `backend/requirements/*.txt` and `frontend/package-lock.json` (CRA Annex I.2). *Roadmap: publish SBOM artifacts per release.*

---

## Dependency Update Policy

| Type | Frequency |
|------|-----------|
| Security patches (critical/high) | Within 14 days of disclosure |
| Security patches (medium) | Within next minor release |
| Non-security updates | Evaluated per release cycle |

---

## Disclosure Policy

This project follows **coordinated disclosure**. Vulnerabilities are disclosed publicly only after a fix is available, or after the 90-day window expires — whichever comes first.

---

## Safe Harbor

We will not pursue or support legal action against security researchers who, in good faith:

- make a genuine effort to avoid privacy violations, data destruction, and service disruption;
- only access or interact with accounts and data they own or have explicit permission to test;
- do not exploit a finding beyond what is necessary to demonstrate it;
- give us reasonable time to remediate before any public disclosure.

Research conducted consistently with this policy is considered **authorized**, and we will
work with you to understand and resolve the issue quickly. Reporters are credited in the
advisory/release notes unless they prefer to remain anonymous.

> Note for testers: report only against deployments you own. Do not test third-party
> installations of this software you do not control — contact that operator instead.
