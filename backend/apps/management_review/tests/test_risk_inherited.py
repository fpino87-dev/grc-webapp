"""Riesame e rischi di gruppo: nel riesame di organizzazione la colonna dei siti
più la riga del gruppo somma il totale; nel riesame di sito i rischi di gruppo
che lo riguardano sono elencati a parte, non sommati."""
import datetime

import pytest

from apps.management_review.models import ManagementReview
from apps.management_review.services.snapshot import generate_snapshot
from apps.risk import services
from apps.risk.tests.test_register import _completed_risk, _eval
from apps.risk.tests.conftest import org_user, other_plant, plant, threats  # noqa: F401


@pytest.mark.django_db
def test_org_and_site_review_with_group_risks(request):
    # Fixture del modulo rischi (importate sopra), lette per nome.
    user, site_a, site_b, th = (
        request.getfixturevalue(name) for name in ("org_user", "plant", "other_plant", "threats")
    )
    services.start_cycle(user, None, "primo")
    services.complete_risk(user, services.create_risk(user, None, {
        **_eval(user), "threat": th["malware"], "affected_plants": [site_a, site_b]}))  # Critical
    services.start_cycle(user, site_a, "primo")
    _completed_risk(user, site_a, th["malware"])  # Critical del sito

    org = ManagementReview.objects.create(title="Org", review_date=datetime.date.today())
    snap = generate_snapshot(org, user)
    sites = snap["siti"]
    group_row = next(s for s in sites if s.get("is_group"))
    assert group_row["rischi_oltre_soglia"] == 1
    assert sum(s["rischi_oltre_soglia"] for s in sites) == snap["rischi"]["oltre_soglia"] == 2
    by_code = {s["code"]: s for s in sites}
    assert by_code[site_a.code]["rischi_ereditati_gruppo"] == 1
    assert by_code[site_b.code]["rischi_ereditati_gruppo"] == 1

    site = ManagementReview.objects.create(title="Sito", review_date=datetime.date.today(), plant=site_a)
    r = generate_snapshot(site, user)["rischi"]
    assert r["oltre_soglia"] == 1  # solo il rischio del sito
    assert r["ereditati_gruppo"]["count"] == 1 and r["ereditati_gruppo"]["untreated_high"] == 1
    assert r["per_obiettivo"][0]["count"] == 1 and r["per_obiettivo"][0]["ereditati"] == 1
