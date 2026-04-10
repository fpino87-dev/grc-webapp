# Contributing

Thank you for contributing to GRC Compliance Platform.

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, production-ready code. Always deployable. |
| `feature/Mnn-short-description` | New feature or module (e.g. `feature/M04-asset-export`) |
| `fix/short-description` | Bug fix (e.g. `fix/evidence-null-expiry`) |
| `security/short-description` | Security fix — keep private until released if sensitive |

Branch from `main`, merge back to `main` via Pull Request.

---

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(scope): short description

feat(assets): add Approved Software List for NIS2/TISAX
fix(controls): nightly task handles null expiry correctly
security(auth): rotate JWT secret on login rate limit breach
docs(manual): update Italian technical manual for M17
chore(deps): bump Django to 5.1.4
```

Types: `feat`, `fix`, `security`, `docs`, `refactor`, `test`, `chore`, `perf`, `i18n`

---

## Pull Request Process

1. **Branch** from `main` using the naming convention above
2. **Write or update tests** — coverage must not drop below 70% globally; aim for ≥ 80% on new modules
3. **Translate all i18n keys** added in `it/common.json` into all 5 languages (IT/EN/FR/PL/TR) — no partial translations
4. **Follow architectural rules** in [CLAUDE.md](./CLAUDE.md) — never bypass them
5. **Open a Pull Request** against `main` with a clear description of what changed and why
6. **1 reviewer required** — the reviewer must approve before merge
7. **Squash and merge** — one clean commit per PR on `main`

### PR Description Template

```
## What
Short description of the change.

## Why
Motivation or issue reference.

## How
Brief implementation notes (if non-obvious).

## Checklist
- [ ] Tests added or updated
- [ ] i18n keys translated in all 5 languages
- [ ] CHANGELOG.md updated under [Unreleased]
- [ ] No secrets or PII in code or logs
- [ ] Architectural rules in CLAUDE.md respected
```

---

## Release Process

Releases are managed by the maintainer. The steps are:

1. Move `[Unreleased]` entries in `CHANGELOG.md` to a new `[X.Y.Z] - YYYY-MM-DD` section
2. Update `VERSION` file to `X.Y.Z`
3. Commit: `chore(release): bump version to X.Y.Z`
4. Tag: `git tag -a vX.Y.Z -m "Release vX.Y.Z"` and `git push origin vX.Y.Z`
5. Create a GitHub Release from the tag, paste the CHANGELOG section as release notes

### Versioning Rules (SemVer)

| Increment | When |
|-----------|------|
| PATCH `0.1.x` | Bug fixes, i18n corrections, minor UI fixes |
| MINOR `0.x.0` | New feature, new module, new language, new integration |
| MAJOR `x.0.0` | Breaking architectural change, non-backward-compatible DB migration |

While `MAJOR == 0`, the API is not considered stable. Breaking changes may occur in MINOR releases.

---

## Architectural Rules

All contributions must comply with the rules in [CLAUDE.md](./CLAUDE.md). Key points:

- All models inherit from `core.models.BaseModel`
- Business logic only in `services.py`
- Every relevant action calls `core.audit.log_action(...)`
- Soft delete always — never `queryset.delete()`
- No N+1 queries — `select_related` / `prefetch_related` required
- No PII in system logs — only counts or anonymous identifiers
- File uploads: always validate with `validate_uploaded_file()` and MIME check

---

## Security Contributions

If your contribution touches authentication, authorization, file upload, audit trail, or the AI Engine, note it explicitly in the PR description and in `CHANGELOG.md` under `### Security`.

To report a vulnerability privately, see [SECURITY.md](./SECURITY.md).
