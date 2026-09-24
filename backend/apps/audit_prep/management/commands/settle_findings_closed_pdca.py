"""
Riallinea i finding collegati a un PDCA già chiuso alla regola di chiusura
introdotta con faee166 (la chiusura del PDCA chiude i finding collegati).

I collegamenti fatti prima lasciavano il finding "in risposta". Per ogni
finding aperto/in risposta con PDCA chiuso si applica la stessa regola della
chiusura del PDCA: CHECK efficace (o assente) con evidenza DO → finding chiuso
con evidenza DO e note ACT (osservazioni/opportunità senza evidenza);
CHECK parziale o NC senza evidenza → resta "in risposta"; CHECK non efficace →
passa al ciclo di riciclo. Idempotente; ogni modifica va nell'audit trail.

Uso:
    python manage.py settle_findings_closed_pdca --user admin@azienda.it          # prova
    python manage.py settle_findings_closed_pdca --user admin@azienda.it --apply  # esegue
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.audit_prep.models import AuditFinding
from apps.audit_prep.services import settle_finding_on_closed_cycle


class Command(BaseCommand):
    help = "Chiude i finding collegati a PDCA già chiusi secondo la regola di chiusura del PDCA."

    def add_arguments(self, parser):
        parser.add_argument("--user", required=True, help="Email dell'utente registrato come autore nell'audit trail")
        parser.add_argument("--apply", action="store_true", help="Esegue le modifiche (senza: solo anteprima)")

    def handle(self, *args, **opts):
        user = get_user_model().objects.filter(email=opts["user"]).first()
        if user is None:
            raise CommandError(f"Utente {opts['user']} non trovato.")
        qs = (
            AuditFinding.objects.filter(status__in=["open", "in_response"], pdca_cycle__fase_corrente="chiuso")
            .select_related("pdca_cycle", "audit_prep", "control_instance")
            .order_by("audit_prep__title", "title")
        )
        findings = list(qs)
        if not findings:
            self.stdout.write("Nessun finding da riallineare.")
            return
        results = {"closed": 0, "in_response": 0, "moved": 0}
        with transaction.atomic():
            for f in findings:
                result = settle_finding_on_closed_cycle(f, f.pdca_cycle, user)
                results[result] = results.get(result, 0) + 1
                self.stdout.write(f"  [{result}] {f.audit_prep.title} — {f.title} (PDCA «{f.pdca_cycle.title}»)")
            if not opts["apply"]:
                transaction.set_rollback(True)
        mode = "ESEGUITO" if opts["apply"] else "ANTEPRIMA (nessuna modifica; usa --apply)"
        self.stdout.write(self.style.SUCCESS(
            f"{mode}: {len(findings)} finding — chiusi {results['closed']}, "
            f"in risposta {results['in_response']}, spostati al riciclo {results['moved']}."
        ))
