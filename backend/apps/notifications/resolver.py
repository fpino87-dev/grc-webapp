"""
Resolver: dato un evento e un contesto (plant, bu)
trova i destinatari reali via UserPlantAccess.
"""

from apps.auth_grc.models import UserPlantAccess

# Ruoli "esterni": persone non interne all'organizzazione (es. auditor di parte
# terza). Non devono mai ricevere via email dati sull'esposizione esterna OSINT,
# anche se un amministratore assegna loro un profilo che include l'evento.
EXTERNAL_ROLES = {"external_auditor"}

# Eventi le cui notifiche restano confinate al personale interno (i ruoli esterni
# vengono filtrati a prescindere dal profilo). L'esposizione OSINT è informazione
# di sicurezza sensibile → solo interni.
INTERNAL_ONLY_EVENTS = {"osint_critical", "supplier_concentration_critical"}


def _user_has_access_to_plant(access: UserPlantAccess, plant) -> bool:
  """Verifica scope accesso utente sul plant."""
  if access.scope_type == "org":
      return True
  if access.scope_type == "bu" and access.scope_bu:
      return plant.bu == access.scope_bu
  if access.scope_type in ("plant_list", "single_plant"):
      return access.scope_plants.filter(pk=plant.pk).exists()
  return False


def resolve_recipients(event_type: str, plant=None, bu=None) -> list:
    """
    Trova i destinatari email per un evento.
    Usa NotificationRoleProfile invece della config granulare.
    Rispetta lo scope: notifica solo utenti con accesso al plant.
    """
    from .models import NotificationRoleProfile

    profiles = NotificationRoleProfile.objects.filter(
        enabled=True,
        deleted_at__isnull=True,
    )

    target_roles = []
    for profile in profiles:
        if event_type in profile.get_active_events():
            target_roles.append(profile.grc_role)

    # Eventi interni-only: rimuovi i ruoli esterni a prescindere dal profilo.
    if event_type in INTERNAL_ONLY_EVENTS:
        target_roles = [r for r in target_roles if r not in EXTERNAL_ROLES]

    if not target_roles:
        return []

    emails: set = set()
    qs = (
        UserPlantAccess.objects.filter(
            role__in=target_roles,
            deleted_at__isnull=True,
        )
        .select_related("user", "scope_bu")
        .prefetch_related("scope_plants")
    )

    for access in qs:
        if not access.user.is_active or not access.user.email:
            continue
        if plant and not _user_has_access_to_plant(access, plant):
            continue
        emails.add(access.user.email)

    return list(emails)


def fire_notification(event_type: str, plant=None, bu=None, context: dict | None = None):
  """
  Entry point principale per inviare una notifica.
  Risolve i destinatari e chiama la funzione email appropriata.
  """
  from .services import (
      notify_document_approval_needed,
      notify_evidence_expired,
      notify_finding_major,
      notify_incident_nis2,
      notify_osint_alert,
      notify_risk_red,
      notify_role_expiring,
      notify_supplier_concentration,
      send_grc_email,
  )

  recipients = resolve_recipients(event_type, plant=plant, bu=bu)
  if not recipients:
      return

  ctx = context or {}

  if event_type == "risk_red" and "assessment" in ctx:
      notify_risk_red(ctx["assessment"], recipients)

  elif event_type == "finding_major" and "finding" in ctx:
      notify_finding_major(ctx["finding"], recipients)

  elif event_type == "finding_minor" and "finding" in ctx:
      notify_finding_major(ctx["finding"], recipients)

  elif event_type == "incident_nis2" and "incident" in ctx:
      notify_incident_nis2(ctx["incident"], recipients)

  elif event_type == "osint_critical" and "alert" in ctx and "entity" in ctx:
      notify_osint_alert(ctx["alert"], ctx["entity"], recipients)

  elif event_type == "supplier_concentration_critical" and "supplier" in ctx:
      notify_supplier_concentration(ctx["supplier"], recipients)

  elif event_type == "evidence_expired" and "instance" in ctx:
      notify_evidence_expired(ctx["instance"], recipients)

  elif event_type == "document_approval" and "document" in ctx:
      notify_document_approval_needed(ctx["document"], recipients)

  elif event_type == "role_expiring" and "assignment" in ctx:
      notify_role_expiring(
          ctx["assignment"],
          ctx.get("days_left", 0),
          recipients,
      )

  elif event_type == "bcp_test_failed":
      plan = ctx.get("plan")
      send_grc_email(
          subject=f"[GRC] Test BCP fallito: {plan.title if plan else ''}",
          body=(
              "Un test BCP ha riportato esito negativo.\n\n"
              f"Piano: {plan.title if plan else '—'}\n"
              f"Plant: {plant.name if plant else '—'}\n\n"
              "È stato aperto un ciclo PDCA automaticamente."
          ),
          recipients=recipients,
      )

  elif event_type == "pdca_blocked":
      cycle = ctx.get("cycle")
      send_grc_email(
          subject=f"[GRC] PDCA bloccato: {cycle.title if cycle else ''}",
          body=(
              "Un ciclo PDCA è bloccato in fase PLAN da oltre 30 giorni.\n\n"
              f"Titolo: {cycle.title if cycle else '—'}\n"
              f"Plant:  {plant.name if plant else '—'}\n\n"
              "Accedi al sistema per avanzare il ciclo."
          ),
          recipients=recipients,
      )

