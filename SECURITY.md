# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

Only the latest release receives security fixes. Older versions are not backported.

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

- Dependencies are reviewed manually on each release using `pip-audit` (backend) and `npm audit` (frontend)
- Security-relevant changes are tagged `security` in CHANGELOG.md
- The audit trail (M10) is append-only and cryptographically chained — tampering is detectable
- No PII reaches external AI services without passing through `Sanitizer.sanitize()` (M20)
- Production deployment uses non-root Docker containers; secrets are never committed to the repository

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
