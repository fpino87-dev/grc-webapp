"""Migrazione dei vecchi dati per persona verso la formazione a evidenze.

Condiviso fra la migrazione dati `0004` e il comando in sola lettura
`check_training_migration_readiness`: entrambi ricevono i model storici (le
tabelle per persona e `framework_refs` non esistono più nei model reali, la
0007 le elimina), così l'anteprima mostra esattamente ciò che la migrazione farà.

- `framework_refs` (stringhe) → `controls` per `external_id`;
- iscrizioni → una sessione `legacy` per corso con i soli conteggi;
- esiti phishing per persona → una sessione `legacy` di phishing per campagna e sito.
"""
from __future__ import annotations

from collections import defaultdict

from django.db.models import Prefetch
from django.utils import timezone

LEGACY_PHISHING_TITLE = "Simulazione di phishing (storico)"

# Ultimo stato dello schema in cui esistono ancora i dati per persona.
LEGACY_STATE_NODE = ("training", "0006_training_evidence_controls")
DATA_MIGRATION_NODE = ("training", "0004_migrate_legacy_training_data")


def legacy_models(connection):
    """Model storici (TrainingCourse, TrainingEnrollment, PhishingSimulation,
    Control, Plant) nello stato `LEGACY_STATE_NODE`, per leggere i dati per
    persona di un DB non ancora migrato."""
    from django.db.migrations.loader import MigrationLoader

    apps = MigrationLoader(connection).project_state(LEGACY_STATE_NODE).apps
    return (
        apps.get_model("training", "TrainingCourse"),
        apps.get_model("training", "TrainingEnrollment"),
        apps.get_model("training", "PhishingSimulation"),
        apps.get_model("controls", "Control"),
        apps.get_model("plants", "Plant"),
    )


def _local_date(dt):
    return timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date()


def plan_legacy_migration(
    TrainingCourse, TrainingEnrollment, PhishingSimulation, Control, Plant,
) -> dict:
    """Calcola, senza scrivere nulla, cosa produrrà la migrazione."""
    # `.only()` sulle colonne esistenti prima della 0003: il comando di anteprima
    # gira con i model dello stato 0006 su un DB non ancora migrato.
    courses = list(
        TrainingCourse.objects.filter(deleted_at__isnull=True)
        .only("id", "title", "framework_refs", "created_at")
        .prefetch_related(Prefetch("plants", queryset=Plant.objects.only("id")))
    )

    refs_by_course = {}
    all_refs = set()
    for c in courses:
        refs = [str(r).strip() for r in (c.framework_refs or []) if str(r).strip()]
        refs_by_course[c.pk] = refs
        all_refs.update(refs)
    controls_by_ref = defaultdict(list)
    for ctrl_id, ext in Control.objects.filter(
        external_id__in=all_refs, deleted_at__isnull=True,
    ).values_list("pk", "external_id"):
        controls_by_ref[ext].append(ctrl_id)

    course_controls = []
    unmatched_refs = []
    for c in courses:
        ids = []
        for ref in refs_by_course[c.pk]:
            if controls_by_ref.get(ref):
                ids.extend(controls_by_ref[ref])
            else:
                unmatched_refs.append({"course": c.title, "ref": ref})
        if ids:
            course_controls.append({"course_id": c.pk, "control_ids": sorted(set(ids), key=str)})

    rows_by_course = defaultdict(list)
    for course_id, st, completed_at in TrainingEnrollment.objects.filter(
        deleted_at__isnull=True,
    ).values_list("course_id", "status", "completed_at"):
        rows_by_course[course_id].append((st, completed_at))

    enrollment_sessions = []
    for c in courses:
        rows = rows_by_course.get(c.pk)
        if not rows:
            continue
        completed = [ca for st, ca in rows if st == "completato"]
        dates = [ca for ca in completed if ca]
        plants = list(c.plants.all())
        enrollment_sessions.append({
            "course_id": c.pk,
            "course": c.title,
            "plant_id": plants[0].pk if len(plants) == 1 else None,
            "held_on": _local_date(max(dates)) if dates else _local_date(c.created_at),
            "target_count": len(rows),
            "trained_count": len(completed),
        })

    groups = defaultdict(lambda: {"sent": 0, "clicked": 0, "reported": 0, "first": None, "kb4": False})
    for sim_id, plant_id, result, sent_at in PhishingSimulation.objects.filter(
        deleted_at__isnull=True,
    ).values_list("kb4_simulation_id", "plant_id", "result", "sent_at"):
        key = (sim_id or f"data:{_local_date(sent_at).isoformat()}", plant_id)
        g = groups[key]
        g["sent"] += 1
        g["clicked"] += result == "clicked"
        g["reported"] += result == "reported"
        g["first"] = sent_at if g["first"] is None else min(g["first"], sent_at)
        g["kb4"] = g["kb4"] or bool(sim_id)
    phishing_sessions = [
        {
            "campaign": key,
            "plant_id": plant_id,
            "held_on": _local_date(g["first"]),
            "sent_count": g["sent"],
            "clicked_count": g["clicked"],
            "reported_count": g["reported"],
            "kb4": g["kb4"],
        }
        for (key, plant_id), g in sorted(groups.items(), key=lambda kv: kv[1]["first"])
    ]

    return {
        "course_controls": course_controls,
        "unmatched_refs": unmatched_refs,
        "enrollment_sessions": enrollment_sessions,
        "phishing_sessions": phishing_sessions,
    }


def apply_legacy_migration(plan: dict, TrainingCourse, TrainingSession) -> None:
    """Scrive quanto calcolato da `plan_legacy_migration`. Idempotente: un corso
    che ha già sessioni `legacy` non viene riaggregato."""
    for row in plan["course_controls"]:
        TrainingCourse.objects.get(pk=row["course_id"]).controls.add(*row["control_ids"])

    already = set(
        TrainingSession.objects.filter(legacy=True).values_list("course_id", flat=True)
    )
    for row in plan["enrollment_sessions"]:
        if row["course_id"] in already:
            continue
        TrainingSession.objects.create(
            course_id=row["course_id"],
            plant_id=row["plant_id"],
            held_on=row["held_on"],
            target_count=row["target_count"],
            trained_count=row["trained_count"],
            legacy=True,
            notes="Storico: iscrizioni individuali aggregate nella migrazione alla formazione a evidenze.",
        )

    if not plan["phishing_sessions"]:
        return
    course = TrainingCourse.objects.filter(
        title=LEGACY_PHISHING_TITLE, kind="phishing", deleted_at__isnull=True,
    ).first()
    if course is None:
        course = TrainingCourse.objects.create(
            title=LEGACY_PHISHING_TITLE,
            kind="phishing",
            source="kb4" if any(r["kb4"] for r in plan["phishing_sessions"]) else "esterno",
            status="archiviato",
            validity_months=12,
        )
    elif course.pk in already:
        return
    for row in plan["phishing_sessions"]:
        TrainingSession.objects.create(
            course=course,
            plant_id=row["plant_id"],
            held_on=row["held_on"],
            sent_count=row["sent_count"],
            clicked_count=row["clicked_count"],
            reported_count=row["reported_count"],
            legacy=True,
            notes="Storico: esiti individuali aggregati nella migrazione alla formazione a evidenze.",
        )
