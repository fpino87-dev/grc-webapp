from .models import AuditPrep


def calc_readiness_score(audit_prep: AuditPrep) -> int:
    """Calculate readiness score 0-100 based on evidence_items status.

    presente counts fully, scaduto counts half, mancante counts zero.
    """
    items = list(audit_prep.evidence_items.all())
    if not items:
        return 0

    total = len(items)
    score = 0
    for item in items:
        if item.status == "presente":
            score += 1
        elif item.status == "scaduto":
            score += 0.5

    return round(score / total * 100)


def update_readiness_score(audit_prep: AuditPrep) -> AuditPrep:
    """Recalculate and persist the readiness_score field."""
    audit_prep.readiness_score = calc_readiness_score(audit_prep)
    audit_prep.save(update_fields=["readiness_score", "updated_at"])
    return audit_prep
