from django.db import transaction
from django.utils import timezone

from .models import RiskAssessment


def normalize_mixed_owner(attrs: dict, user_field: str, text_field: str) -> dict:
    """
    Responsabile "misto" (utente del portale OPPURE testo libero): i due valori
    sono alternativi. Se nel payload c'è un utente il testo viene svuotato; il
    testo viene ripulito dagli spazi. Si toccano solo i campi presenti nel
    payload, così un PATCH parziale non cancella l'altro valore.
    """
    if text_field in attrs:
        attrs[text_field] = (attrs[text_field] or "").strip()
    if attrs.get(user_field) is not None:
        attrs[text_field] = ""
    elif attrs.get(text_field):
        # Testo inviato (anche da solo, su un record che aveva un utente): vince il testo.
        attrs[user_field] = None
    return attrs


def mixed_owner_name(user, external: str) -> str | None:
    """Nome visualizzato del responsabile misto (utente o testo libero)."""
    if user is not None:
        return f"{user.first_name} {user.last_name}".strip() or user.email
    return external or None


def get_risk_bia_bcp_context(assessment: RiskAssessment) -> dict:
    """Vista integrata di un rischio: processo BIA collegato e BCP che lo coprono."""
    from django.db.models import Q

    from apps.bcp.models import BcpPlan

    risk_data = {
        "id": str(assessment.pk),
        "name": risk_label(assessment),
        "asset_type": assessment.asset_type,
        "asset_id": str(assessment.asset_id) if assessment.asset_id else None,
        "probability": assessment.probability,
        "impact": assessment.impact,
        "current_class": assessment.current_class,
        "expected_class": assessment.expected_class,
        "status": assessment.status,
        "treatment": assessment.treatment,
    }
    bia_data = None
    bcp_plans = []
    bcp_summary = None
    process = assessment.critical_process
    if process:
        bia_data = {
            "process_id": str(process.pk),
            "process_name": process.name,
            "plant_id": str(process.plant_id),
            "criticality": process.criticality,
            "mtpd_hours": process.mtpd_hours,
            "rto_target_hours": process.rto_target_hours,
            "rpo_target_hours": process.rpo_target_hours,
            "status": process.status,
        }
        plans = BcpPlan.objects.filter(deleted_at__isnull=True).filter(
            Q(critical_process=process) | Q(critical_processes=process)
        ).distinct()
        for p in plans:
            bcp_plans.append({
                "id": str(p.pk), "title": p.title, "plant_id": str(p.plant_id), "status": p.status,
                "rto_hours": p.rto_hours, "rpo_hours": p.rpo_hours,
                "last_test_date": p.last_test_date, "next_test_date": p.next_test_date,
            })
        bcp_summary = {
            "has_bcp_covering_process": bool(bcp_plans),
            "best_rto_vs_mtpd_status": process.rto_bcp_status,
        }
    return {"risk": risk_data, "bia": bia_data, "bcp_plans": bcp_plans, "bcp_summary": bcp_summary}


# ─────────────────────────────────────────────────────────────────────────────
# Metodologia di risk management — regole uniche di calcolo, governo e cicli.
# Ogni modulo che mostra o usa classi di rischio passa da queste funzioni.
# ─────────────────────────────────────────────────────────────────────────────

RISK_CLASSES = ("very_low", "low", "medium", "high", "critical")

# Matrice probabilità × impatto della procedura (§8): la classe si legge solo
# da qui, mai dal prodotto numerico. Costante: garantisce confrontabilità.
_MATRIX = {
    5: ("medium", "high", "high", "critical", "critical"),
    4: ("low", "medium", "high", "critical", "critical"),
    3: ("low", "medium", "medium", "high", "critical"),
    2: ("very_low", "low", "medium", "high", "high"),
    1: ("very_low", "low", "low", "medium", "high"),
}

IMPACT_DIMENSIONS = ("economic", "legal", "customer", "reputational", "people", "operational")

# Soglia minima d'impatto per perdita di riservatezza, dalla classe di
# protezione dell'informazione (§7.2, criterio del white paper VDA).
CONFIDENTIALITY_FLOOR = {"very_high": 5, "high": 4, "normal": 3, "low": 2}

# Regola di trattamento e scadenza per classe (§9.2).
TREATMENT_RULES = {
    "critical": {"rule": "mandatory", "months": 3},
    "high": {"rule": "evaluate", "months": 12},
    "medium": {"rule": "acceptable", "months": 24},
    "low": {"rule": "acceptable", "months": 60},
    "very_low": {"rule": "acceptable", "months": 60},
}


def risk_class(probability, impact) -> str | None:
    """Classe di rischio dalla matrice; None se manca uno dei due valori."""
    try:
        p, i = int(probability), int(impact)
    except (TypeError, ValueError):
        return None
    row = _MATRIX.get(p)
    if row is None or not 1 <= i <= 5:
        return None
    return row[i - 1]


def class_rank(cls: str | None) -> int:
    """Posizione della classe (0 = very_low … 4 = critical); -1 se assente."""
    return RISK_CLASSES.index(cls) if cls in RISK_CLASSES else -1


def shift_class(cls: str, delta: int, floor: str | None = None) -> str:
    """Override del Risk Owner (§8): sposta di `delta` livelli, mai sotto `floor`."""
    rank = max(0, min(len(RISK_CLASSES) - 1, class_rank(cls) + delta))
    if floor is not None:
        rank = max(rank, class_rank(floor))
    return RISK_CLASSES[rank]


def confidentiality_floor(levels) -> int | None:
    """Impatto minimo dato dalle classi di protezione delle informazioni colpite."""
    values = [CONFIDENTIALITY_FLOOR[lv] for lv in levels if lv in CONFIDENTIALITY_FLOOR]
    return max(values) if values else None


def overall_impact(dimensions: dict, floor: int | None = None) -> int | None:
    """Impatto finale = caso peggiore fra le dimensioni valorizzate e la soglia minima."""
    values = [int(v) for k, v in (dimensions or {}).items() if k in IMPACT_DIMENSIONS and v]
    if floor:
        values.append(int(floor))
    return max(values) if values else None


def risk_level_bucket(cls: str | None) -> str | None:
    """Semaforo verde/giallo/rosso per i moduli che non usano le 5 classi."""
    if cls in ("very_low", "low"):
        return "verde"
    if cls == "medium":
        return "giallo"
    if cls in ("high", "critical"):
        return "rosso"
    return None


def treatment_rule(cls: str | None) -> dict | None:
    return TREATMENT_RULES.get(cls)


# ── Policy di governo del rischio ────────────────────────────────────────────

DEFAULT_ECONOMIC_THRESHOLDS = {
    # Limite inferiore in euro di ciascun livello; sotto il livello 2 = livello 1.
    "5": 500000,
    "4": 250000,
    "3": 50000,
    "2": 10000,
}

_SITE_ACCEPT = {"roles": ["risk_owner"], "scope": "plant", "requires_body": False}

PRESETS = {
    "centralizzato": {
        "group_register_enabled": True,
        "acceptance_matrix": {
            "very_low": _SITE_ACCEPT,
            "low": _SITE_ACCEPT,
            "medium": {**_SITE_ACCEPT, "notify": ["site_risk_manager"]},
            "high": {"roles": ["risk_owner", "plant_manager"], "scope": "plant", "requires_body": False},
            "critical": {"roles": [], "scope": "org", "requires_body": True},
        },
        "upper_opinion": {"very_low": "none", "low": "none", "medium": "none",
                          "high": "binding", "critical": "binding"},
    },
    "federato": {
        "group_register_enabled": True,
        "acceptance_matrix": {
            "very_low": _SITE_ACCEPT,
            "low": _SITE_ACCEPT,
            "medium": {**_SITE_ACCEPT, "notify": ["site_risk_manager"]},
            "high": {"roles": ["risk_owner", "plant_manager"], "scope": "plant", "requires_body": False},
            "critical": {"roles": [], "scope": "plant", "requires_body": True},
        },
        "upper_opinion": {"very_low": "none", "low": "none", "medium": "none",
                          "high": "notify", "critical": "binding"},
    },
    "sito_singolo": {
        "group_register_enabled": False,
        "acceptance_matrix": {
            "very_low": _SITE_ACCEPT,
            "low": _SITE_ACCEPT,
            "medium": _SITE_ACCEPT,
            "high": {"roles": ["risk_owner", "plant_manager"], "scope": "plant", "requires_body": False},
            "critical": {"roles": [], "scope": "plant", "requires_body": True},
        },
        "upper_opinion": {c: "none" for c in RISK_CLASSES},
    },
}

_COMMON_DEFAULTS = {
    "acceptance_max_months": {"very_low": 12, "low": 12, "medium": 12, "high": 12, "critical": 6},
    "economic_thresholds": DEFAULT_ECONOMIC_THRESHOLDS,
    "overdue_escalation_days": 30,
    "review_frequency_months": 12,
}

OPINION_MODES = ("none", "notify", "binding")
_POLICY_DICT_FIELDS = ("acceptance_matrix", "upper_opinion", "acceptance_max_months", "economic_thresholds")
_POLICY_SCALAR_FIELDS = ("group_register_enabled", "overdue_escalation_days", "review_frequency_months")


def default_preset() -> str:
    """Senza policy: un solo sito attivo → sito singolo, altrimenti centralizzato."""
    from apps.plants.models import Plant

    return "centralizzato" if Plant.objects.filter(status="attivo").count() > 1 else "sito_singolo"


def preset_defaults(preset: str) -> dict:
    import copy

    base = copy.deepcopy(PRESETS[preset])
    base.update(copy.deepcopy(_COMMON_DEFAULTS))
    return base


def resolve_policy(plant=None) -> dict:
    """Policy effettiva per un registro: preset → organizzazione → sito.

    Per i campi dizionario (per classe o per livello) l'override è chiave per
    chiave; per gli scalari vale il valore più specifico non nullo.
    """
    from .models import RiskGovernancePolicy

    org = RiskGovernancePolicy.objects.filter(plant__isnull=True).first()
    site = (
        RiskGovernancePolicy.objects.filter(plant=plant).first()
        if plant is not None else None
    )
    preset = org.preset if org else default_preset()
    effective = preset_defaults(preset)
    for layer in (org, site):
        if layer is None:
            continue
        for field in _POLICY_DICT_FIELDS:
            override = getattr(layer, field) or {}
            effective[field] = {**effective[field], **override}
        for field in _POLICY_SCALAR_FIELDS:
            value = getattr(layer, field)
            if value is not None:
                effective[field] = value
    effective["preset"] = preset
    effective["configured"] = org is not None
    effective["org_policy_id"] = str(org.pk) if org else None
    effective["plant_policy_id"] = str(site.pk) if site else None
    return effective


def economic_level(amount, thresholds: dict) -> int:
    """Livello d'impatto economico (1–5) di un importo in euro."""
    for level in ("5", "4", "3", "2"):
        if amount >= thresholds[level]:
            return int(level)
    return 1


def _validate_policy_data(data: dict) -> None:
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    for field in ("acceptance_matrix", "upper_opinion", "acceptance_max_months"):
        unknown = set((data.get(field) or {})) - set(RISK_CLASSES)
        if unknown:
            raise ValidationError(_("Classi di rischio non valide: %(classes)s") % {"classes": ", ".join(sorted(unknown))})
    for mode in (data.get("upper_opinion") or {}).values():
        if mode not in OPINION_MODES:
            raise ValidationError(_("Modalità di parere non valida: %(mode)s") % {"mode": mode})
    for cls, rule in (data.get("acceptance_matrix") or {}).items():
        if not isinstance(rule, dict) or rule.get("scope") not in ("plant", "org"):
            raise ValidationError(_("Regola di accettazione non valida per la classe %(cls)s") % {"cls": cls})
    for months in (data.get("acceptance_max_months") or {}).values():
        if not isinstance(months, int) or months < 1:
            raise ValidationError(_("La validità dell'accettazione deve essere un numero di mesi positivo."))
    thresholds = data.get("economic_thresholds") or {}
    if thresholds:
        if set(thresholds) != {"2", "3", "4", "5"}:
            raise ValidationError(_("Le soglie economiche richiedono i livelli 2, 3, 4 e 5."))
        values = [thresholds[k] for k in ("2", "3", "4", "5")]
        if any(not isinstance(v, (int, float)) or v <= 0 for v in values) or values != sorted(set(values)):
            raise ValidationError(_("Le soglie economiche devono essere positive e crescenti dal livello 2 al 5."))


def save_governance_policy(user, plant, data: dict):
    """Crea o aggiorna la policy di un perimetro (organizzazione o sito).

    Le regole di governo le decide chi ha scope di organizzazione, anche le
    eccezioni per un singolo sito (procedura §1: la capogruppo approva).
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _
    from rest_framework.exceptions import PermissionDenied

    from core.audit import log_action
    from core.scoping import user_has_org_scope

    from .models import RiskGovernancePolicy

    if not user_has_org_scope(user):
        raise PermissionDenied(_("Solo chi ha accesso a tutta l'organizzazione può modificare il governo del rischio."))
    if "preset" in data and data["preset"] not in PRESETS:
        raise ValidationError(_("Preset non valido."))
    if plant is not None and "preset" in data:
        raise ValidationError(_("Il preset si sceglie solo a livello di organizzazione."))
    _validate_policy_data(data)

    allowed = set(_POLICY_DICT_FIELDS) | set(_POLICY_SCALAR_FIELDS) | {"preset", "notes"}
    with transaction.atomic():
        policy = RiskGovernancePolicy.objects.filter(plant=plant).first()
        created = policy is None
        if created:
            policy = RiskGovernancePolicy(plant=plant, created_by=user)
        for key, value in data.items():
            if key in allowed:
                setattr(policy, key, value)
        policy.approved_by = user
        policy.approved_at = timezone.now()
        policy.save()
        log_action(
            user=user,
            action_code="risk.policy.updated",
            level="L1",
            entity=policy,
            payload={
                "plant_id": str(plant.pk) if plant else None,
                "created": created,
                "fields": sorted(k for k in data if k in allowed),
            },
        )
    return policy


# ── Catalogo minacce ─────────────────────────────────────────────────────────

_THREAT_CODE_RE = r"^[A-Z0-9_]{2,30}$"


def _validate_threat_fields(asset_types, cia) -> None:
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from .models import ASSET_TYPES

    if not asset_types or set(asset_types) - set(ASSET_TYPES):
        raise ValidationError(_("Tipologie di asset non valide."))
    if set(cia or []) - {"C", "I", "A"}:
        raise ValidationError(_("Le proprietà colpite possono essere solo C, I, A."))


def sync_threat_catalog(data: dict) -> dict:
    """Allinea le voci `source=catalog` al file JSON del catalogo.

    Upsert per codice; le voci sparite dal file vengono disattivate (i rischi
    le referenziano). Le voci personalizzate non vengono toccate: se un codice
    del file coincide con una voce custom, la voce custom resta e il codice del
    file viene segnalato come conflitto.
    """
    from .models import ThreatCatalogEntry

    version = str(data.get("version", ""))
    counts = {"created": 0, "updated": 0, "deactivated": 0, "conflicts": []}
    seen = set()
    with transaction.atomic():
        for item in data.get("threats", []):
            code = item["code"]
            seen.add(code)
            _validate_threat_fields(item.get("asset_types"), item.get("cia"))
            entry = ThreatCatalogEntry.objects.filter(code=code).first()
            if entry and entry.source == "custom":
                counts["conflicts"].append(code)
                continue
            values = {
                "asset_types": item["asset_types"],
                "cia": item.get("cia", []),
                "translations": item.get("translations", {}),
                "source": "catalog",
                "catalog_version": version,
                "active": True,
            }
            if entry is None:
                ThreatCatalogEntry.objects.create(code=code, **values)
                counts["created"] += 1
            else:
                for key, value in values.items():
                    setattr(entry, key, value)
                entry.save()
                counts["updated"] += 1
        counts["deactivated"] = (
            ThreatCatalogEntry.objects.filter(source="catalog", active=True)
            .exclude(code__in=seen)
            .update(active=False)
        )
    return counts


def _require_org_scope_for_catalog(user) -> None:
    from django.utils.translation import gettext as _
    from rest_framework.exceptions import PermissionDenied

    from core.scoping import user_has_org_scope

    if not user_has_org_scope(user):
        raise PermissionDenied(_("Solo chi ha accesso a tutta l'organizzazione può gestire il catalogo minacce."))


def create_custom_threat(user, *, code, asset_types, cia, translations):
    import re

    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action

    from .models import ThreatCatalogEntry

    _require_org_scope_for_catalog(user)
    code = (code or "").strip().upper()
    if not re.match(_THREAT_CODE_RE, code):
        raise ValidationError(_("Il codice deve avere da 2 a 30 caratteri fra lettere maiuscole, cifre e trattino basso."))
    if ThreatCatalogEntry.objects.filter(code=code).exists():
        raise ValidationError(_("Esiste già una minaccia con questo codice."))
    _validate_threat_fields(asset_types, cia)
    translations = _clean_threat_translations(translations)
    with transaction.atomic():
        entry = ThreatCatalogEntry.objects.create(
            code=code, asset_types=asset_types, cia=cia or [], translations=translations,
            source="custom", created_by=user,
        )
        log_action(user=user, action_code="risk.catalog.custom_created", level="L2",
                   entity=entry, payload={"code": code})
    return entry


def seed_business_objectives(items) -> int:
    """Crea gli obiettivi aziendali proposti mancanti (per codice, di gruppo).
    Non tocca quelli esistenti né ricrea quelli eliminati da Impostazioni."""
    from .models import BusinessObjective

    existing = set(BusinessObjective.objects.all_with_deleted().exclude(code="").values_list("code", flat=True))
    created = 0
    for order, item in enumerate(items or [], start=1):
        if item.get("code") in existing:
            continue
        dims = [d for d in item.get("impact_dimensions", []) if d in IMPACT_DIMENSIONS]
        BusinessObjective.objects.create(
            code=item["code"], name=item["name"], description=item.get("description", ""),
            impact_dimensions=dims, order=order,
        )
        created += 1
    return created


THREAT_LANGS = ("it", "en", "fr", "pl", "tr")


def _clean_threat_translations(translations) -> dict:
    """Titoli per lingua di una voce personalizzata: l'inglese è obbligatorio
    (lingua di ripiego per i siti che usano una lingua non compilata)."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    clean = {}
    for lang in THREAT_LANGS:
        title = ((translations or {}).get(lang) or {}).get("title", "")
        if isinstance(title, str) and title.strip():
            clean[lang] = {"title": title.strip()}
    if "en" not in clean:
        raise ValidationError(_("Indica almeno il titolo della minaccia in inglese."))
    return clean


def update_custom_threat(user, entry, **fields):
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action

    _require_org_scope_for_catalog(user)
    if entry.source != "custom":
        raise ValidationError(_("Le voci del catalogo di gruppo non si modificano da qui."))
    asset_types = fields.get("asset_types", entry.asset_types)
    cia = fields.get("cia", entry.cia)
    _validate_threat_fields(asset_types, cia)
    if "translations" in fields:
        fields["translations"] = _clean_threat_translations(fields["translations"])
    with transaction.atomic():
        for key in ("asset_types", "cia", "translations", "active"):
            if key in fields:
                setattr(entry, key, fields[key])
        entry.save()
        log_action(user=user, action_code="risk.catalog.custom_updated", level="L2",
                   entity=entry, payload={"code": entry.code, "fields": sorted(fields)})
    return entry


def deactivate_threat(user, entry):
    """Disattiva una voce personalizzata (i rischi già valutati la conservano)."""
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action

    _require_org_scope_for_catalog(user)
    if entry.source != "custom":
        raise ValidationError(_("Le voci del catalogo di gruppo non si disattivano da qui."))
    with transaction.atomic():
        entry.active = False
        entry.save(update_fields=["active", "updated_at"])
        log_action(user=user, action_code="risk.catalog.custom_deactivated", level="L2",
                   entity=entry, payload={"code": entry.code})
    return entry


# ── Perimetro della valutazione ──────────────────────────────────────────────

def plant_handles_prototypes(plant) -> bool:
    """Un sito gestisce prototipi se ha attivo il framework TISAX prototipi."""
    from apps.plants.models import PlantFramework

    if plant is None:
        return False
    return PlantFramework.objects.filter(
        plant=plant, framework__code="TISAX_PROTO", active=True,
    ).exists()


def asset_types_present(plant) -> list:
    """Tipologie di asset da coprire nel registro (procedura §6.5).

    Sito: IT, Sede e Personale sempre; OT se il sito ha OT; Fornitori se ha
    fornitori attivi propri o di organizzazione (senza sito: valgono per tutti
    i siti); Prototipi se gestisce prototipi. Gruppo: IT, Personale e
    Fornitori (servizi condivisi, strutture e contratti della capogruppo).
    """
    from django.db.models import Q

    from apps.assets.models import Asset
    from apps.suppliers.models import Supplier

    if plant is None:
        return ["IT", "PERSONALE", "FORNITORI"]
    types = ["IT"]
    if plant.has_ot or Asset.objects.filter(plant=plant, asset_type="OT").exists():
        types.append("OT")
    types += ["SEDE", "PERSONALE"]
    if Supplier.objects.filter(
        Q(plants=plant) | Q(plants__isnull=True), status="attivo",
    ).exists():
        types.append("FORNITORI")
    if plant_handles_prototypes(plant):
        types.append("PROTOTIPI")
    return types


# ── Cicli di valutazione ─────────────────────────────────────────────────────

def open_cycle(plant=None):
    """Ciclo in corso o in approvazione del registro (sito o gruppo), se c'è."""
    from .models import RiskAssessmentCycle

    return RiskAssessmentCycle.objects.filter(
        plant=plant, status__in=RiskAssessmentCycle.OPEN_STATUSES,
    ).first()


def approved_cycle(plant=None):
    """Ultimo ciclo approvato del registro: è la valutazione vigente."""
    from .models import RiskAssessmentCycle

    return (
        RiskAssessmentCycle.objects.filter(plant=plant, status="approvato")
        .order_by("-approved_at", "-started_at").first()
    )


def start_cycle(user, plant, kind: str, trigger_reason: str = ""):
    """Avvia una valutazione del registro di un sito (o del gruppo se plant è None).

    - `primo`: solo se il registro non ha ancora valutazioni con il metodo
      attuale (i cicli `legacy` non contano);
    - `periodico` / `straordinario`: richiedono una valutazione approvata;
      lo straordinario richiede il motivo (trigger, §11.2).
    """
    from django.core.exceptions import ValidationError
    from django.utils.translation import gettext as _

    from core.audit import log_action
    from core.scoping import require_org_scope_for_org_wide, require_plant_access

    from .models import RiskAssessmentCycle

    if kind not in ("primo", "periodico", "straordinario"):
        raise ValidationError(_("Tipo di valutazione non valido."))
    if plant is None:
        require_org_scope_for_org_wide(user, None)
        if not resolve_policy(None)["group_register_enabled"]:
            raise ValidationError(_("Il registro di gruppo non è attivo nella policy di governo del rischio."))
    else:
        require_plant_access(user, plant)
    if open_cycle(plant):
        raise ValidationError(_("C'è già una valutazione aperta per questo registro."))
    current_method = RiskAssessmentCycle.objects.filter(plant=plant).exclude(kind="legacy")
    if kind == "primo" and current_method.exists():
        raise ValidationError(_("Il primo risk assessment è già stato avviato per questo registro."))
    if kind != "primo" and not current_method.filter(status__in=("approvato", "archiviato")).exists():
        raise ValidationError(_("Serve una valutazione approvata prima di una revisione."))
    if kind == "straordinario" and not (trigger_reason or "").strip():
        raise ValidationError(_("Indica il motivo della revisione straordinaria."))

    with transaction.atomic():
        cycle = RiskAssessmentCycle.objects.create(
            plant=plant, kind=kind, trigger_reason=(trigger_reason or "").strip(),
            status="in_corso", started_at=timezone.now(), created_by=user,
        )
        log_action(
            user=user, action_code="risk.cycle.started", level="L1", entity=cycle,
            payload={"plant_id": str(plant.pk) if plant else None, "kind": kind},
        )
    return cycle


# ─────────────────────────────────────────────────────────────────────────────
# Registro, valutazione e monitoraggio (procedura §5–§11)
# ─────────────────────────────────────────────────────────────────────────────

# Campi che costituiscono la valutazione: si modificano solo con un ciclo in
# corso sul registro. Piani, verifiche, accettazioni sono monitoraggio.
EVALUATION_FIELDS = (
    "name", "asset_type", "asset", "asset_group_label", "supplier", "threat",
    "critical_process", "vulnerability", "consequence",
    "probability", "probability_method", "probability_rationale",
    "impact_economic", "impact_legal", "impact_customer", "impact_reputational",
    "impact_people", "impact_operational", "impact_rationale",
    "class_override", "override_rationale", "legal_or_contract_violation",
    "treatment", "treatment_rationale", "expected_probability", "expected_impact",
    "owner", "treatment_owner", "treatment_owner_external", "plan_due_date",
    "nis2_in_scope", "nis2_art21_category", "impacted_systems",
    "significant_incident_potential", "significant_incident_note",
)
EVALUATION_M2M = ("information_classes", "affected_plants", "business_objectives")


def _err(message, **params):
    from django.core.exceptions import ValidationError

    return ValidationError(message % params if params else message)


def risk_label(risk, lang: str | None = None) -> str:
    """Nome del rischio da mostrare: quello scritto dall'utente oppure il titolo
    della minaccia nella lingua di chi guarda (default: lingua attiva)."""
    if risk.name:
        return risk.name
    if risk.threat_id:
        from django.utils.translation import get_language

        return risk.threat.get_title((lang or get_language() or "en")[:2])
    return "—"


def is_legacy(risk) -> bool:
    return risk.cycle_id is not None and risk.cycle.kind == "legacy"


def register_queryset(plant=None, include_inherited: bool = False):
    """Rischi del registro corrente (sito o gruppo), esclusi quelli legacy.

    Con `include_inherited` il registro di un sito comprende anche i rischi di
    gruppo che il sito eredita (in sola lettura, procedura §4.3).
    """
    from django.db.models import Q

    base = RiskAssessment.objects.exclude(cycle__kind="legacy")
    if plant is None:
        return base.filter(plant__isnull=True)
    q = Q(plant=plant)
    if include_inherited:
        q |= Q(plant__isnull=True, affected_plants=plant)
    return base.filter(q).distinct()


def require_register_write(user, plant) -> None:
    """Scrittura sul registro: per il gruppo serve lo scope di organizzazione."""
    from core.scoping import require_org_scope_for_org_wide, require_plant_access

    if plant is None:
        require_org_scope_for_org_wide(user, None)
    else:
        require_plant_access(user, plant)


def _require_evaluation_cycle(plant):
    from django.utils.translation import gettext as _

    cycle = open_cycle(plant)
    if cycle is None or cycle.status != "in_corso":
        raise _err(_("La valutazione si modifica solo con una valutazione in corso sul registro."))
    return cycle


def _require_not_legacy(risk) -> None:
    from django.utils.translation import gettext as _

    if is_legacy(risk):
        raise _err(_("Il rischio appartiene alla valutazione precedente (metodo superato): è in sola lettura."))


def recompute_risk(risk) -> None:
    """Ricalcola impatto, classe attuale e classe attesa con le regole uniche.

    Le classi di informazioni (M2M) contano solo a rischio salvato.
    """
    dims = {d: getattr(risk, f"impact_{d}") for d in IMPACT_DIMENSIONS}
    floor = None
    if risk.pk and risk.threat_id and "C" in (risk.threat.cia or []):
        floor = confidentiality_floor(risk.information_classes.values_list("confidentiality", flat=True))
    risk.impact = overall_impact(dims, floor)
    risk.matrix_class = risk_class(risk.probability, risk.impact) or ""
    if risk.matrix_class:
        floor_cls = risk_class(risk.probability, floor) if floor else None
        risk.current_class = shift_class(risk.matrix_class, int(risk.class_override or 0), floor_cls)
    else:
        risk.current_class = ""
    risk.expected_class = risk_class(risk.expected_probability, risk.expected_impact) or ""


def _validate_risk_links(risk, information_classes, affected_plants, business_objectives=None) -> None:
    """Coerenza fra registro, tipologia, minaccia e oggetti collegati."""
    from django.utils.translation import gettext as _

    from .models import ASSET_TYPES

    plant = risk.plant
    if risk.asset_type and risk.asset_type not in ASSET_TYPES:
        raise _err(_("Tipologie di asset non valide."))
    if risk.threat_id:
        if not risk.threat.active:
            raise _err(_("La minaccia scelta non è più attiva nel catalogo."))
        if risk.asset_type and risk.asset_type not in risk.threat.asset_types:
            raise _err(_("La minaccia scelta non si applica a questa tipologia di asset."))
    if risk.asset_id and plant is not None and risk.asset.plant_id != plant.pk:
        raise _err(_("L'asset deve appartenere al sito del registro."))
    if risk.critical_process_id and plant is not None and risk.critical_process.plant_id != plant.pk:
        raise _err(_("Il processo deve appartenere al sito del registro."))
    # Un fornitore senza siti è di organizzazione e vale per tutti i siti.
    if risk.supplier_id and plant is not None and risk.supplier.plants.exists() \
            and not risk.supplier.plants.filter(pk=plant.pk).exists():
        raise _err(_("Il fornitore deve operare per il sito del registro."))
    for ic in information_classes or []:
        if ic.plant_id is not None and (plant is None or ic.plant_id != plant.pk):
            raise _err(_("Le classi di informazioni devono essere del sito del registro o di gruppo."))
    for bo in business_objectives or []:
        if bo.plant_id is not None and (plant is None or bo.plant_id != plant.pk):
            raise _err(_("Gli obiettivi aziendali devono essere del sito del registro o di gruppo."))
    if affected_plants and plant is not None:
        raise _err(_("Solo i rischi di gruppo indicano i siti che li ereditano."))
    if risk.class_override not in (-1, 0, 1):
        raise _err(_("L'override della classe può spostare al massimo di un livello."))


def _apply_fields(risk, data: dict) -> dict:
    """Copia i campi di valutazione presenti in `data`; ritorna le M2M."""
    for field in EVALUATION_FIELDS:
        if field in data:
            setattr(risk, field, data[field])
    normalize_mixed_owner_obj(risk)
    return {field: data[field] for field in EVALUATION_M2M if field in data}


def normalize_mixed_owner_obj(risk) -> None:
    """Responsabile del trattamento: utente del portale OPPURE testo libero."""
    if risk.treatment_owner_id:
        risk.treatment_owner_external = ""


def _default_nis2_scope(risk, affected_plants) -> bool:
    if risk.plant is not None:
        return risk.plant.is_nis2_subject
    return any(p.is_nis2_subject for p in (affected_plants or []))


def _close_stale_acceptance(user, risk) -> None:
    """Un'accettazione vale per la classe accettata: se la classe cambia decade."""
    from django.utils.translation import gettext as _

    for acc in risk.acceptances.filter(status__in=("pending", "active")):
        if acc.risk_class != risk.current_class:
            _close_acceptance(user, acc, "revoked", _("La classe del rischio è cambiata."))


def create_risk(user, plant, data: dict):
    """Nuovo rischio nel registro di `plant` (None = gruppo), dentro il ciclo in corso."""
    from django.utils.translation import gettext as _

    from core.audit import log_action

    require_register_write(user, plant)
    cycle = _require_evaluation_cycle(plant)
    risk = RiskAssessment(plant=plant, cycle=cycle, evaluated_in_cycle=cycle, status="bozza", created_by=user)
    m2m = _apply_fields(risk, data)
    if not risk.asset_type or not risk.threat_id:
        raise _err(_("Indica la tipologia di asset e la minaccia del catalogo."))
    _validate_risk_links(risk, m2m.get("information_classes"), m2m.get("affected_plants"),
                         m2m.get("business_objectives"))
    if "nis2_in_scope" not in data:
        risk.nis2_in_scope = _default_nis2_scope(risk, m2m.get("affected_plants"))
    with transaction.atomic():
        recompute_risk(risk)
        risk.save()
        for field, values in m2m.items():
            getattr(risk, field).set(values)
        recompute_risk(risk)
        risk.save()
        log_action(
            user=user, action_code="risk.created", level="L2", entity=risk,
            payload={"cycle_id": str(cycle.pk), "threat": risk.threat.code, "asset_type": risk.asset_type},
        )
    return risk


def update_risk(user, risk, data: dict):
    """Modifica della valutazione: rimette il rischio in bozza nel ciclo in corso."""
    from core.audit import log_action

    _require_not_legacy(risk)
    require_register_write(user, risk.plant)
    cycle = _require_evaluation_cycle(risk.plant)
    m2m = _apply_fields(risk, data)
    _validate_risk_links(
        risk,
        m2m.get("information_classes", list(risk.information_classes.all())),
        m2m.get("affected_plants", list(risk.affected_plants.all())) if risk.plant is None
        else m2m.get("affected_plants"),
        m2m.get("business_objectives"),
    )
    before = risk.current_class
    with transaction.atomic():
        for field, values in m2m.items():
            getattr(risk, field).set(values)
        recompute_risk(risk)
        risk.status = "bozza"
        risk.evaluated_in_cycle = cycle
        risk.save()
        log_action(
            user=user, action_code="risk.updated", level="L2", entity=risk,
            payload={"fields": sorted(k for k in data if k in EVALUATION_FIELDS or k in EVALUATION_M2M),
                     "class_before": before, "class_after": risk.current_class},
        )
    return risk


def risk_completeness_errors(risk) -> list:
    """Cosa manca per completare la valutazione (procedura §7–§9)."""
    from django.utils.translation import gettext as _

    errors = []
    if not risk.applicable:
        if not risk.not_applicable_reason.strip():
            errors.append(_("Motiva perché la minaccia non è applicabile."))
        return errors
    if not risk.business_objectives.exists():
        errors.append(_("Indica almeno un obiettivo aziendale minacciato dal rischio."))
    if not risk.probability or not risk.probability_rationale.strip():
        errors.append(_("Indica la probabilità e la sua motivazione."))
    if not risk.impact or not risk.impact_rationale.strip():
        errors.append(_("Indica almeno una dimensione d'impatto e la motivazione."))
    if risk.class_override and not risk.override_rationale.strip():
        errors.append(_("Motiva lo spostamento della classe."))
    if not risk.owner_id:
        errors.append(_("Indica il Risk Owner."))
    if not risk.treatment:
        errors.append(_("Scegli il trattamento."))
    rule = treatment_rule(risk.current_class) or {}
    if risk.treatment == "accettare" and rule.get("rule") in ("mandatory", "evaluate") \
            and not risk.treatment_rationale.strip():
        errors.append(_("Per un rischio High o Critical non trattato serve la motivazione (analisi costi/benefici)."))
    if risk.treatment in ("mitigare", "evitare", "trasferire") and not risk.expected_class:
        errors.append(_("Indica il rischio atteso dopo il trattamento."))
    return errors


def complete_risk(user, risk):
    """Chiude la valutazione del rischio nel ciclo in corso."""
    from core.audit import log_action

    _require_not_legacy(risk)
    require_register_write(user, risk.plant)
    cycle = _require_evaluation_cycle(risk.plant)
    recompute_risk(risk)
    errors = risk_completeness_errors(risk)
    if errors:
        raise _err(errors[0])
    with transaction.atomic():
        risk.status = "completato"
        risk.assessed_by = user
        risk.assessed_at = timezone.now()
        risk.evaluated_in_cycle = cycle
        if risk.applicable and not risk.plan_due_date and treatment_rule(risk.current_class):
            months = treatment_rule(risk.current_class)["months"]
            risk.plan_due_date = timezone.localdate() + timezone.timedelta(days=30 * months)
        risk.save()
        _close_stale_acceptance(user, risk)
        log_action(
            user=user, action_code="risk.completed", level="L2", entity=risk,
            payload={"class": risk.current_class, "treatment": risk.treatment, "applicable": risk.applicable},
        )
        if risk.applicable and risk.current_class in ("high", "critical"):
            _escalate_high_risk(risk)
    return risk


def confirm_risk(user, risk):
    """Revisione periodica: conferma un rischio valutato senza modificarlo."""
    from django.utils.translation import gettext as _

    from core.audit import log_action

    _require_not_legacy(risk)
    require_register_write(user, risk.plant)
    cycle = _require_evaluation_cycle(risk.plant)
    if risk.status != "completato":
        raise _err(_("Si conferma solo un rischio con valutazione completata."))
    # Si conferma solo ciò che rispetta le regole attuali (es. obiettivi aziendali).
    errors = risk_completeness_errors(risk)
    if errors:
        raise _err(errors[0])
    with transaction.atomic():
        risk.evaluated_in_cycle = cycle
        risk.assessed_by = user
        risk.assessed_at = timezone.now()
        risk.save(update_fields=["evaluated_in_cycle", "assessed_by", "assessed_at", "updated_at"])
        log_action(user=user, action_code="risk.confirmed", level="L2", entity=risk,
                   payload={"cycle_id": str(cycle.pk), "class": risk.current_class})
    return risk


def reopen_risk(user, risk):
    from core.audit import log_action

    _require_not_legacy(risk)
    require_register_write(user, risk.plant)
    _require_evaluation_cycle(risk.plant)
    with transaction.atomic():
        risk.status = "bozza"
        risk.save(update_fields=["status", "updated_at"])
        log_action(user=user, action_code="risk.reopened", level="L2", entity=risk, payload={})
    return risk


def mark_not_applicable(user, plant, asset_type: str, threat, reason: str):
    """Copertura (§6.5): la coppia tipologia × minaccia non si applica al registro."""
    from django.utils.translation import gettext as _

    from core.audit import log_action

    if not (reason or "").strip():
        raise _err(_("Motiva perché la minaccia non è applicabile."))
    require_register_write(user, plant)
    cycle = _require_evaluation_cycle(plant)
    risk = RiskAssessment(
        plant=plant, cycle=cycle, evaluated_in_cycle=cycle, asset_type=asset_type, threat=threat,
        applicable=False, not_applicable_reason=reason.strip(),
        status="completato", assessed_by=user, assessed_at=timezone.now(), created_by=user,
    )
    _validate_risk_links(risk, [], [])
    with transaction.atomic():
        risk.save()
        log_action(user=user, action_code="risk.marked_not_applicable", level="L2", entity=risk,
                   payload={"threat": threat.code, "asset_type": asset_type})
    return risk


def delete_risk(user, risk) -> None:
    """Toglie un rischio dal registro durante una valutazione in corso."""
    from django.utils.translation import gettext as _

    from core.audit import log_action

    _require_not_legacy(risk)
    require_register_write(user, risk.plant)
    _require_evaluation_cycle(risk.plant)
    with transaction.atomic():
        for acc in risk.acceptances.filter(status__in=("pending", "active")):
            _close_acceptance(user, acc, "revoked", _("Rischio eliminato dal registro."))
        for plan in risk.mitigation_plans.all():
            plan.soft_delete()
        for measure in risk.existing_measures.all():
            measure.soft_delete()
        risk.soft_delete()
        log_action(user=user, action_code="risk.deleted", level="L2", entity=risk,
                   payload={"class": risk.current_class})


def _escalate_high_risk(risk) -> None:
    """High/Critical completato: task per il piano di trattamento se manca e
    notifica "rischio critico" (dopo il commit)."""
    from django.utils.translation import gettext as _

    from apps.auth_grc.models import GrcRole
    from apps.tasks.services import create_task

    if risk.treatment in ("mitigare", "evitare", "trasferire") and not risk.mitigation_plans.exists():
        months = treatment_rule(risk.current_class)["months"]
        create_task(
            plant=risk.plant,
            title=_("Piano di trattamento rischio %(cls)s — %(name)s") % {
                "cls": risk.current_class, "name": risk_label(risk)},
            priority="critica" if risk.current_class == "critical" else "alta",
            source_module="M06",
            source_id=risk.pk,
            due_date=timezone.localdate() + timezone.timedelta(days=min(30, 30 * months)),
            assign_type="role",
            assign_value=GrcRole.RISK_MANAGER,
        )

    def _notify():
        try:
            from apps.notifications.resolver import fire_notification

            fire_notification("risk_red", plant=risk.plant, context={"assessment": risk})
        except Exception:  # noqa: BLE001 — la notifica non blocca mai la valutazione
            pass

    transaction.on_commit(_notify)


# ── Misure esistenti, piani e verifica ───────────────────────────────────────

def save_existing_measure(user, risk, data: dict, measure=None):
    from core.audit import log_action

    from .models import RiskExistingMeasure

    _require_not_legacy(risk)
    require_register_write(user, risk.plant)
    _require_evaluation_cycle(risk.plant)
    ci = data.get("control_instance")
    if ci is not None and risk.plant is not None and ci.plant_id != risk.plant_id:
        from django.utils.translation import gettext as _

        raise _err(_("Il controllo deve essere del sito del registro."))
    with transaction.atomic():
        measure = measure or RiskExistingMeasure(risk=risk, created_by=user)
        for field in ("control_instance", "description", "effectiveness"):
            if field in data:
                setattr(measure, field, data[field])
        measure.save()
        log_action(user=user, action_code="risk.existing_measure.saved", level="L2", entity=risk,
                   payload={"measure_id": str(measure.pk)})
    return measure


def delete_existing_measure(user, measure) -> None:
    from core.audit import log_action

    _require_not_legacy(measure.risk)
    require_register_write(user, measure.risk.plant)
    _require_evaluation_cycle(measure.risk.plant)
    with transaction.atomic():
        measure.soft_delete()
        log_action(user=user, action_code="risk.existing_measure.deleted", level="L2", entity=measure.risk,
                   payload={"measure_id": str(measure.pk)})


def require_plan_write(user, risk) -> None:
    """Piani di trattamento: monitoraggio, ammesso fuori dai cicli ma non sul legacy."""
    _require_not_legacy(risk)
    require_register_write(user, risk.plant)


def verify_mitigation_plan(user, plan, note: str = ""):
    """Verifica di efficacia di una misura completata (§9.4)."""
    from django.utils.translation import gettext as _

    from core.audit import log_action

    require_plan_write(user, plan.assessment)
    if not plan.completed_at:
        raise _err(_("Si verifica solo una misura completata."))
    with transaction.atomic():
        plan.verified_at = timezone.now()
        plan.verified_by = user
        plan.verification_note = (note or "").strip()
        plan.save(update_fields=["verified_at", "verified_by", "verification_note", "updated_at"])
        log_action(user=user, action_code="risk.mitigation.verified", level="L1", entity=plan,
                   payload={"risk_id": str(plan.assessment_id)})
    return plan


def can_apply_expected(risk) -> bool:
    plans = list(risk.mitigation_plans.all())
    return bool(
        risk.expected_class and plans
        and all(p.completed_at and p.verified_at for p in plans)
    )


def apply_expected_risk(user, risk, note: str = ""):
    """Misure attuate e verificate: il rischio atteso diventa rischio attuale.

    La probabilità prende quella attesa; ogni dimensione d'impatto viene
    limitata all'impatto atteso (la soglia di riservatezza resta valida).
    """
    from django.utils.translation import gettext as _

    from core.audit import log_action

    require_plan_write(user, risk)
    if not can_apply_expected(risk):
        raise _err(_("Il rischio atteso si applica solo con tutte le misure completate e verificate."))
    before = risk.current_class
    with transaction.atomic():
        risk.probability = risk.expected_probability
        for dim in IMPACT_DIMENSIONS:
            value = getattr(risk, f"impact_{dim}")
            if value:
                setattr(risk, f"impact_{dim}", min(value, risk.expected_impact))
        risk.class_override = 0
        recompute_risk(risk)
        risk.save()
        _close_stale_acceptance(user, risk)
        log_action(user=user, action_code="risk.expected_applied", level="L1", entity=risk,
                   payload={"class_before": before, "class_after": risk.current_class,
                            "note": (note or "")[:200]})
    return risk


# ── Accettazione (§10) ───────────────────────────────────────────────────────

def user_holds_role(user, role: str, plant) -> bool:
    """Il ruolo (GRC o normativo) copre il sito? Lo scope org copre tutti."""
    from django.db.models import Q

    from apps.auth_grc.models import UserPlantAccess
    from apps.governance.models import RoleAssignment
    from core.scoping import user_can_access_plant

    today = timezone.localdate()
    assignments = RoleAssignment.objects.filter(
        user=user, role=role, valid_from__lte=today,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
    if assignments.filter(scope_type="org").exists():
        return True
    if plant is not None and assignments.filter(scope_type="plant", scope_id=plant.pk).exists():
        return True
    access = UserPlantAccess.objects.filter(user=user, role=role)
    if access.filter(scope_type="org").exists():
        return True
    return plant is not None and access.exists() and user_can_access_plant(user, plant)


def can_give_opinion(user) -> bool:
    """Parere del livello superiore: CISO nominato con scope organizzazione;
    senza un CISO nominato, un Compliance Officer di organizzazione."""
    from django.db.models import Q

    from apps.auth_grc.models import GrcRole, UserPlantAccess
    from apps.governance.models import NormativeRole, RoleAssignment

    today = timezone.localdate()
    active_ciso = RoleAssignment.objects.filter(
        role=NormativeRole.CISO, scope_type="org", valid_from__lte=today,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=today))
    if active_ciso.exists():
        return active_ciso.filter(user=user).exists()
    return UserPlantAccess.objects.filter(
        user=user, role=GrcRole.COMPLIANCE_OFFICER, scope_type="org",
    ).exists()


def acceptance_requirements(risk) -> dict:
    """Chi deve firmare, se serve l'organo, il parere e la validità massima."""
    policy = resolve_policy(risk.plant)
    cls = risk.current_class
    rule = policy["acceptance_matrix"].get(cls) or {}
    roles = list(rule.get("roles", []))
    # Chi ha valutato e tratta da solo il proprio rischio non lo accetta da
    # solo: serve il livello superiore (§10). Vale solo se a firmare sarebbe
    # proprio lui (come Risk Owner o perché ricopre tutti i ruoli richiesti):
    # se accetta un altro ruolo, per esempio il solo CISO, il controllo
    # indipendente c'è già.
    self_managed = (
        risk.owner_id is not None and risk.owner_id == risk.assessed_by_id
        and risk.treatment_owner_id in (None, risk.owner_id) and not risk.treatment_owner_external.strip()
    )
    signs_alone = bool(roles) and (
        "risk_owner" in roles or all(user_holds_role(risk.owner, r, risk.plant) for r in roles)
    ) if self_managed else False
    added_for_self_management = (
        signs_alone and "plant_manager" not in roles and not rule.get("requires_body")
    )
    if added_for_self_management:
        roles.append("plant_manager")
    return {
        "added_for_self_management": added_for_self_management,
        "class": cls,
        "roles": roles,
        "scope": rule.get("scope", "plant"),
        "requires_body": bool(rule.get("requires_body")),
        "notify": list(rule.get("notify", [])),
        "upper_opinion": policy["upper_opinion"].get(cls, "none"),
        "max_months": int(policy["acceptance_max_months"].get(cls, 12)),
        "not_acceptable": risk.legal_or_contract_violation,
    }


def signable_roles(user, acceptance) -> list:
    risk = acceptance.risk
    signed_roles = {s["role"] for s in acceptance.signatures}
    signed_users = {s["user_id"] for s in acceptance.signatures}
    if user.pk in signed_users:
        return []
    out = []
    for role in acceptance.required_roles:
        if role in signed_roles:
            continue
        if role == "risk_owner":
            if risk.owner_id == user.pk:
                out.append(role)
        elif user_holds_role(user, role, risk.plant):
            out.append(role)
    return out


def request_acceptance(user, risk, *, rationale: str, expires_on=None, body=None, body_resolution_ref: str = ""):
    """Avvia l'accettazione del rischio attuale secondo la policy (§10)."""
    import datetime

    from django.utils.translation import gettext as _

    from apps.auth_grc.models import GrcRole
    from apps.tasks.services import create_task
    from core.audit import log_action

    from .models import RiskAcceptance

    require_plan_write(user, risk)
    if risk.status != "completato" or not risk.applicable or not risk.current_class:
        raise _err(_("Si accetta solo un rischio applicabile con valutazione completata."))
    req = acceptance_requirements(risk)
    if req["not_acceptable"]:
        raise _err(_("Il rischio comporta una violazione di legge, di requisiti VDA ISA o di obblighi di riservatezza: non è accettabile."))
    if risk.acceptances.filter(status__in=("pending", "active")).exists():
        raise _err(_("C'è già un'accettazione in corso o attiva per questo rischio."))
    if not (rationale or "").strip():
        raise _err(_("La motivazione dell'accettazione è obbligatoria."))
    today = timezone.localdate()
    limit = today + datetime.timedelta(days=30 * req["max_months"])
    expires_on = expires_on or limit
    if expires_on > limit or expires_on <= today:
        raise _err(_("La scadenza dell'accettazione deve essere futura ed entro %(months)s mesi."),
                   months=req["max_months"])
    if req["requires_body"] and req["scope"] == "org":
        from core.scoping import require_org_scope_for_org_wide

        require_org_scope_for_org_wide(user, None)

    with transaction.atomic():
        acc = RiskAcceptance.objects.create(
            risk=risk, risk_class=req["class"], required_roles=req["roles"],
            requires_body=req["requires_body"], body=body, body_resolution_ref=(body_resolution_ref or "").strip(),
            rationale=rationale.strip(), expires_on=expires_on,
            upper_opinion="pending" if req["upper_opinion"] == "binding" else "not_required",
            created_by=user,
        )
        for role in signable_roles(user, acc)[:1]:
            acc.signatures = [{"role": role, "user_id": user.pk, "at": timezone.now().isoformat()}]
            acc.save(update_fields=["signatures", "updated_at"])
        log_action(user=user, action_code="risk.acceptance.requested", level="L1", entity=risk,
                   payload={"acceptance_id": str(acc.pk), "class": acc.risk_class,
                            "expires_on": str(expires_on)})
        if req["upper_opinion"] in ("binding", "notify"):
            create_task(
                plant=risk.plant,
                title=(_("Parere sull'accettazione del rischio — %(name)s") if req["upper_opinion"] == "binding"
                       else _("Informativa: accettazione del rischio — %(name)s")) % {"name": risk_label(risk)},
                priority="alta" if req["upper_opinion"] == "binding" else "bassa",
                source_module="M06", source_id=risk.pk,
                due_date=today + datetime.timedelta(days=14),
                assign_type="role", assign_value=GrcRole.COMPLIANCE_OFFICER,
            )
        if req["notify"]:
            create_task(
                plant=risk.plant,
                title=_("Informativa: accettazione del rischio — %(name)s") % {"name": risk_label(risk)},
                priority="bassa", source_module="M06", source_id=risk.pk,
                due_date=today + datetime.timedelta(days=14),
                assign_type="role", assign_value=GrcRole.RISK_MANAGER,
            )
        _try_activate(user, acc)
    return acc


def sign_acceptance(user, acceptance):
    from django.utils.translation import gettext as _

    from core.audit import log_action

    if acceptance.status != "pending":
        raise _err(_("L'accettazione non è più in approvazione."))
    roles = signable_roles(user, acceptance)
    if not roles:
        raise _err(_("Non hai un ruolo che possa firmare questa accettazione."))
    with transaction.atomic():
        acceptance.signatures = [*acceptance.signatures,
                                 {"role": roles[0], "user_id": user.pk, "at": timezone.now().isoformat()}]
        acceptance.save(update_fields=["signatures", "updated_at"])
        log_action(user=user, action_code="risk.acceptance.signed", level="L1", entity=acceptance.risk,
                   payload={"acceptance_id": str(acceptance.pk), "role": roles[0]})
        _try_activate(user, acceptance)
    return acceptance


def record_body_decision(user, acceptance, *, body, resolution_ref: str):
    """Delibera dell'organo per un'accettazione che la richiede (Critical)."""
    from django.utils.translation import gettext as _

    from core.audit import log_action

    if acceptance.status != "pending" or not acceptance.requires_body:
        raise _err(_("Questa accettazione non attende una delibera dell'organo."))
    if body is None or not (resolution_ref or "").strip():
        raise _err(_("Indica l'organo e il riferimento della delibera."))
    plant = None if resolve_policy(acceptance.risk.plant)["acceptance_matrix"].get(
        acceptance.risk_class, {}).get("scope") == "org" else acceptance.risk.plant
    require_register_write(user, plant)
    with transaction.atomic():
        acceptance.body = body
        acceptance.body_resolution_ref = resolution_ref.strip()
        acceptance.save(update_fields=["body", "body_resolution_ref", "updated_at"])
        log_action(user=user, action_code="risk.acceptance.body_decision", level="L1",
                   entity=acceptance.risk, payload={"acceptance_id": str(acceptance.pk)})
        _try_activate(user, acceptance)
    return acceptance


def give_opinion(user, acceptance, *, favorable: bool, note: str = ""):
    from django.utils.translation import gettext as _

    from core.audit import log_action

    if acceptance.status != "pending" or acceptance.upper_opinion != "pending":
        raise _err(_("Questa accettazione non attende un parere."))
    if not can_give_opinion(user):
        raise _err(_("Il parere spetta al CISO."))
    if not favorable and not (note or "").strip():
        raise _err(_("Motiva il parere contrario."))
    with transaction.atomic():
        acceptance.upper_opinion = "favorable" if favorable else "unfavorable"
        acceptance.opinion_by = user
        acceptance.opinion_at = timezone.now()
        acceptance.opinion_note = (note or "").strip()
        acceptance.save(update_fields=["upper_opinion", "opinion_by", "opinion_at", "opinion_note", "updated_at"])
        log_action(user=user, action_code="risk.opinion.given", level="L1", entity=acceptance.risk,
                   payload={"acceptance_id": str(acceptance.pk), "favorable": favorable})
        if favorable:
            _try_activate(user, acceptance)
        else:
            _close_acceptance(user, acceptance, "rejected", acceptance.opinion_note)
    return acceptance


def revoke_acceptance(user, acceptance, reason: str):
    from django.utils.translation import gettext as _

    if acceptance.status not in ("pending", "active"):
        raise _err(_("L'accettazione è già chiusa."))
    if not (reason or "").strip():
        raise _err(_("Indica il motivo della revoca."))
    require_plan_write(user, acceptance.risk)
    _close_acceptance(user, acceptance, "revoked", reason.strip())
    return acceptance


def _close_acceptance(user, acceptance, status: str, reason: str) -> None:
    from core.audit import log_action

    acceptance.status = status
    acceptance.closed_at = timezone.now()
    acceptance.close_reason = reason or ""
    acceptance.save(update_fields=["status", "closed_at", "close_reason", "updated_at"])
    log_action(user=user, action_code=f"risk.acceptance.{status}", level="L1", entity=acceptance.risk,
               payload={"acceptance_id": str(acceptance.pk)})


def _try_activate(user, acceptance) -> None:
    from core.audit import log_action

    signed = {s["role"] for s in acceptance.signatures}
    if not set(acceptance.required_roles) <= signed:
        return
    if acceptance.requires_body and not (acceptance.body_id and acceptance.body_resolution_ref):
        return
    if acceptance.upper_opinion == "pending":
        return
    acceptance.status = "active"
    acceptance.activated_at = timezone.now()
    acceptance.save(update_fields=["status", "activated_at", "updated_at"])
    log_action(user=user, action_code="risk.acceptance.granted", level="L1", entity=acceptance.risk,
               payload={"acceptance_id": str(acceptance.pk), "class": acceptance.risk_class,
                        "expires_on": str(acceptance.expires_on)})


def expire_acceptances(today=None) -> dict:
    """Scadenze delle accettazioni: avviso a 30 giorni, scadenza il giorno dopo."""
    import datetime

    from django.contrib.auth import get_user_model
    from django.utils.translation import gettext as _

    from apps.auth_grc.models import GrcRole
    from apps.tasks.services import create_task

    from .models import RiskAcceptance

    today = today or timezone.localdate()
    system_user = get_user_model().objects.filter(is_superuser=True).first()
    counts = {"warned": 0, "expired": 0}
    active = RiskAcceptance.objects.filter(status="active").select_related("risk", "risk__plant", "risk__threat")
    for acc in active.filter(expires_on__lt=today):
        with transaction.atomic():
            if system_user:
                _close_acceptance(system_user, acc, "expired", _("Accettazione scaduta."))
            else:
                acc.status, acc.closed_at = "expired", timezone.now()
                acc.save(update_fields=["status", "closed_at", "updated_at"])
            create_task(
                plant=acc.risk.plant,
                title=_("Accettazione scaduta: trattare o riaccettare il rischio — %(name)s") % {"name": risk_label(acc.risk)},
                priority="alta", source_module="M06", source_id=acc.risk_id,
                due_date=today + datetime.timedelta(days=7),
                assign_type="role", assign_value=GrcRole.RISK_MANAGER,
            )
        counts["expired"] += 1
    for acc in active.filter(expires_on__gte=today,
                             expires_on__lte=today + datetime.timedelta(days=ACCEPTANCE_WARN_DAYS),
                             expiry_warned_at__isnull=True):
        with transaction.atomic():
            create_task(
                plant=acc.risk.plant,
                title=_("Accettazione del rischio in scadenza il %(date)s — %(name)s") % {
                    "date": acc.expires_on.isoformat(), "name": risk_label(acc.risk)},
                priority="media", source_module="M06", source_id=acc.risk_id,
                due_date=acc.expires_on,
                assign_type="role", assign_value=GrcRole.RISK_MANAGER,
            )
            acc.expiry_warned_at = timezone.now()
            acc.save(update_fields=["expiry_warned_at", "updated_at"])
        counts["warned"] += 1
    return counts


def escalate_overdue_plans(today=None) -> dict:
    """Misure in ritardo (§11.3): avviso al Risk Manager, poi escalation al
    livello di organizzazione oltre la soglia della policy (subito per i Critical)."""
    from django.utils.translation import gettext as _

    from apps.auth_grc.models import GrcRole
    from apps.tasks.services import create_task

    from .models import RiskMitigationPlan

    today = today or timezone.localdate()
    counts = {"notified": 0, "escalated": 0}
    overdue = (
        RiskMitigationPlan.objects.filter(completed_at__isnull=True, due_date__lt=today)
        .exclude(assessment__cycle__kind="legacy")
        .filter(assessment__deleted_at__isnull=True)
        .select_related("assessment", "assessment__plant", "assessment__threat")
    )
    for plan in overdue:
        risk = plan.assessment
        days_late = (today - plan.due_date).days
        threshold = resolve_policy(risk.plant)["overdue_escalation_days"]
        critical = risk.current_class == "critical"
        if plan.escalation_level < 2 and (critical or days_late > threshold):
            create_task(
                plant=risk.plant,
                title=_("Escalation: misura in ritardo di %(days)s giorni — %(name)s") % {
                    "days": days_late, "name": risk_label(risk)},
                priority="critica" if critical else "alta",
                source_module="M06", source_id=risk.pk, due_date=today + timezone.timedelta(days=7),
                assign_type="role", assign_value=GrcRole.COMPLIANCE_OFFICER,
            )
            plan.escalation_level = 2
            plan.save(update_fields=["escalation_level", "updated_at"])
            counts["escalated"] += 1
        elif plan.escalation_level == 0:
            create_task(
                plant=risk.plant,
                title=_("Misura del piano di trattamento in ritardo — %(name)s") % {"name": risk_label(risk)},
                priority="media", source_module="M06", source_id=risk.pk,
                due_date=today + timezone.timedelta(days=7),
                assign_type="role", assign_value=GrcRole.RISK_MANAGER,
            )
            plan.escalation_level = 1
            plan.save(update_fields=["escalation_level", "updated_at"])
            counts["notified"] += 1
    return counts


# ── Rischi ereditati (§4.3) ──────────────────────────────────────────────────

def report_local_impact(user, risk, plant, *, local_impact: int, note: str):
    from django.utils.translation import gettext as _

    from core.audit import log_action
    from core.scoping import require_plant_access

    from .models import RiskLocalImpactReport

    require_plant_access(user, plant)
    if risk.plant_id is not None or not risk.affected_plants.filter(pk=plant.pk).exists():
        raise _err(_("Si segnala l'impatto locale solo di un rischio di gruppo ereditato dal sito."))
    if not (note or "").strip() or local_impact not in range(1, 6):
        raise _err(_("Indica l'impatto locale (1–5) e la motivazione."))
    with transaction.atomic():
        report = RiskLocalImpactReport.objects.create(
            risk=risk, plant=plant, local_impact=local_impact, note=note.strip(), created_by=user,
        )
        log_action(user=user, action_code="risk.local_impact.reported", level="L2", entity=risk,
                   payload={"plant_id": str(plant.pk), "local_impact": local_impact})
    return report


def acknowledge_local_impact(user, report):
    from django.utils.translation import gettext as _

    from core.audit import log_action
    from core.scoping import require_org_scope_for_org_wide

    require_org_scope_for_org_wide(user, None)
    if report.status != "aperta":
        raise _err(_("La segnalazione è già stata recepita."))
    with transaction.atomic():
        report.status = "recepita"
        report.acknowledged_by = user
        report.acknowledged_at = timezone.now()
        report.save(update_fields=["status", "acknowledged_by", "acknowledged_at", "updated_at"])
        log_action(user=user, action_code="risk.local_impact.acknowledged", level="L2", entity=report.risk,
                   payload={"report_id": str(report.pk)})
    return report


# ── Copertura, invio e approvazione dei cicli ────────────────────────────────

COVERAGE_STATE_LABELS = {
    "evaluated": "Valutata", "draft": "In valutazione", "missing": "Da valutare",
    "not_applicable": "Non applicabile", "inherited": "Coperta dal gruppo",
}


def register_coverage(plant=None) -> dict:
    """Copertura del registro (§6.5): ogni minaccia applicabile a ogni
    tipologia presente va valutata o dichiarata non applicabile."""
    from .models import ThreatCatalogEntry

    types = asset_types_present(plant)
    threats = list(ThreatCatalogEntry.objects.filter(active=True))
    fields = ("id", "asset_type", "threat_id", "applicable", "status", "current_class")
    risks = list(register_queryset(plant).filter(threat__isnull=False).values(*fields))
    by_pair: dict = {}
    for r in risks:
        by_pair.setdefault((r["asset_type"], r["threat_id"]), []).append(r)
    # Rischi di gruppo ereditati dal sito (§4.3): la coppia è coperta dal gruppo,
    # che la valuta e la tratta; il sito non la duplica né la dichiara non applicabile.
    inherited: dict = {}
    if plant is not None:
        group_risks = (
            RiskAssessment.objects.exclude(cycle__kind="legacy")
            .filter(plant__isnull=True, affected_plants=plant, applicable=True, threat__isnull=False)
            .distinct().values(*fields)
        )
        for r in group_risks:
            inherited.setdefault((r["asset_type"], r["threat_id"]), []).append(r)
    pairs = []
    for asset_type in types:
        for threat in threats:
            if asset_type not in threat.asset_types:
                continue
            found = by_pair.get((asset_type, threat.pk), [])
            from_group = inherited.get((asset_type, threat.pk), []) if not found else []
            if from_group:
                state = "inherited"
                found = from_group
            elif not found:
                state = "missing"
            elif any(r["status"] != "completato" for r in found):
                state = "draft"
            elif any(r["applicable"] for r in found):
                state = "evaluated"
            else:
                state = "not_applicable"
            pairs.append({
                "asset_type": asset_type, "threat_id": str(threat.pk), "threat_code": threat.code,
                "state": state, "risk_ids": [str(r["id"]) for r in found],
                "worst_class": max((r["current_class"] for r in found if r["applicable"]),
                                   key=class_rank, default=""),
            })
    total = len(pairs)
    closed = sum(1 for p in pairs if p["state"] in ("evaluated", "not_applicable", "inherited"))
    return {
        "asset_types": types,
        "pairs": pairs,
        "total": total,
        "closed": closed,
        "missing": sum(1 for p in pairs if p["state"] == "missing"),
        "pct": round(closed / total * 100, 1) if total else 100.0,
    }


def cycle_submission_errors(cycle) -> list:
    from django.utils.translation import gettext as _

    errors = []
    register = register_queryset(cycle.plant)
    if register.filter(status="bozza").exists():
        errors.append(_("Ci sono rischi con valutazione non completata."))
    if cycle.kind in ("primo", "periodico"):
        if register.filter(applicable=True).exclude(evaluated_in_cycle=cycle).exists():
            errors.append(_("Ci sono rischi non ancora valutati o confermati in questa valutazione."))
        coverage = register_coverage(cycle.plant)
        if coverage["closed"] < coverage["total"]:
            errors.append(_("La copertura del catalogo minacce non è completa."))
    return errors


def submit_cycle(user, cycle):
    from django.utils.translation import gettext as _

    from core.audit import log_action

    require_register_write(user, cycle.plant)
    if cycle.status != "in_corso":
        raise _err(_("Si invia in approvazione solo una valutazione in corso."))
    errors = cycle_submission_errors(cycle)
    if errors:
        raise _err(errors[0])
    with transaction.atomic():
        cycle.status = "in_approvazione"
        cycle.save(update_fields=["status", "updated_at"])
        log_action(user=user, action_code="risk.cycle.submitted", level="L1", entity=cycle,
                   payload={"plant_id": str(cycle.plant_id) if cycle.plant_id else None})
    return cycle


def return_cycle(user, cycle, reason: str):
    from django.utils.translation import gettext as _

    from core.audit import log_action

    require_register_write(user, cycle.plant)
    if cycle.status != "in_approvazione":
        raise _err(_("La valutazione non è in approvazione."))
    if not (reason or "").strip():
        raise _err(_("Indica il motivo del rinvio."))
    with transaction.atomic():
        cycle.status = "in_corso"
        cycle.save(update_fields=["status", "updated_at"])
        log_action(user=user, action_code="risk.cycle.returned", level="L1", entity=cycle,
                   payload={"reason": reason.strip()[:200]})
    return cycle


def _cycle_approver_plant(cycle):
    """Chi approva: nel modello centralizzato e per il gruppo decide
    l'organizzazione; altrimenti chi ha accesso al sito (§1, §10)."""
    if cycle.plant is None or resolve_policy(cycle.plant)["preset"] == "centralizzato":
        return None
    return cycle.plant


def build_register_snapshot(plant, cycle) -> dict:
    """Fotografia del registro all'approvazione: storico per audit ed export."""
    from .models import RiskAcceptance

    risks = (
        register_queryset(plant)
        .select_related("threat", "owner", "asset", "supplier", "critical_process")
        .prefetch_related("mitigation_plans", "affected_plants", "business_objectives", "information_classes")
        .order_by("asset_type", "threat__code")
    )
    active_acc = {
        a.risk_id: a for a in RiskAcceptance.objects.filter(risk__in=risks, status="active")
    }
    items = []
    for r in risks:
        acc = active_acc.get(r.pk)
        items.append({
            "id": str(r.pk),
            "name": risk_label(r),
            "asset_type": r.asset_type,
            "threat": r.threat.code if r.threat else None,
            "applicable": r.applicable,
            "not_applicable_reason": r.not_applicable_reason,
            "asset": r.asset.name if r.asset else (r.asset_group_label or None),
            "supplier": r.supplier.name if r.supplier else None,
            "process": r.critical_process.name if r.critical_process else None,
            "business_objectives": [bo.name for bo in r.business_objectives.all()],
            "information_classes": [ic.name for ic in r.information_classes.all()],
            "probability": r.probability,
            "impact": r.impact,
            "impacts": {d: getattr(r, f"impact_{d}") for d in IMPACT_DIMENSIONS},
            "current_class": r.current_class,
            "expected_class": r.expected_class,
            "treatment": r.treatment,
            "owner_id": r.owner_id,
            "plans": [{"action": p.action, "due_date": str(p.due_date),
                       "completed": bool(p.completed_at), "verified": bool(p.verified_at)}
                      for p in r.mitigation_plans.all()],
            "acceptance": {"class": acc.risk_class, "expires_on": str(acc.expires_on)} if acc else None,
            "affected_plants": [str(p.pk) for p in r.affected_plants.all()],
        })
    return {
        "taken_at": timezone.now().isoformat(),
        "kind": cycle.kind,
        "risks": items,
        "coverage": {k: v for k, v in register_coverage(plant).items() if k != "pairs"},
        "objectives": [{k: v for k, v in o.items() if k not in ("risk_ids", "inherited_risk_ids")} for o in register_objectives(plant)],
        "information_coverage": [{k: v for k, v in i.items() if k != "risk_ids"} for i in information_coverage(plant)],
        "policy": resolve_policy(plant),
    }


def approve_cycle(user, cycle, *, body, review=None, local_adoption_ref: str = ""):
    """Approvazione dell'organo: congela il registro e archivia la valutazione precedente."""
    from django.utils.translation import gettext as _

    from core.audit import log_action

    from .models import RiskAssessmentCycle

    if cycle.status != "in_approvazione":
        raise _err(_("Si approva solo una valutazione inviata in approvazione."))
    if body is None:
        raise _err(_("Indica l'organo che approva la valutazione."))
    require_register_write(user, _cycle_approver_plant(cycle))
    with transaction.atomic():
        RiskAssessmentCycle.objects.filter(plant=cycle.plant, status="approvato").exclude(pk=cycle.pk).update(
            status="archiviato", closed_at=timezone.now(),
        )
        cycle.snapshot = build_register_snapshot(cycle.plant, cycle)
        cycle.status = "approvato"
        cycle.approved_by_body = body
        cycle.approval_review = review
        cycle.approved_at = timezone.now()
        cycle.closed_at = cycle.approved_at
        cycle.local_adoption_ref = (local_adoption_ref or "").strip()
        cycle.save()
        log_action(user=user, action_code="risk.cycle.approved", level="L1", entity=cycle,
                   payload={"plant_id": str(cycle.plant_id) if cycle.plant_id else None,
                            "risks": len(cycle.snapshot["risks"])})
    return cycle


def revaluation_triggers(plant) -> list:
    """Eventi dopo l'ultima approvazione che suggeriscono una revisione
    straordinaria (procedura §11.2). Calcolati, non memorizzati."""
    from apps.assets.models import Asset
    from apps.audit_prep.models import AuditFinding
    from apps.controls.models import ControlInstance
    from apps.incidents.models import Incident

    from .models import RiskMitigationPlan

    approved = approved_cycle(plant)
    since = approved.approved_at if approved else None
    out = []
    today = timezone.localdate()
    overdue = RiskMitigationPlan.objects.filter(
        assessment__in=register_queryset(plant), completed_at__isnull=True, due_date__lt=today,
    ).count()
    if overdue:
        out.append({"kind": "overdue_measures", "count": overdue})
    if since is None or plant is None:
        return out
    incidents = Incident.objects.filter(plant=plant, created_at__gt=since).filter(
        models_q_significant_incident(),
    ).count()
    if incidents:
        out.append({"kind": "significant_incidents", "count": incidents})
    new_assets = Asset.objects.filter(plant=plant, created_at__gt=since, criticality__gte=4).count()
    if new_assets:
        out.append({"kind": "new_critical_assets", "count": new_assets})
    changed = Asset.objects.filter(
        plant=plant, last_change_date__gt=since.date(), risk_assessments__in=register_queryset(plant),
    ).distinct().count()
    if changed:
        out.append({"kind": "changed_assets", "count": changed})
    findings = AuditFinding.objects.filter(
        audit_prep__plant=plant, created_at__gt=since, finding_type="major_nc",
    ).count()
    if findings:
        out.append({"kind": "major_findings", "count": findings})
    gaps = ControlInstance.objects.filter(plant=plant, status="gap", updated_at__gt=since).count()
    if gaps:
        out.append({"kind": "control_gaps", "count": gaps})
    return out


def models_q_significant_incident():
    from django.db.models import Q

    return Q(is_significant=True) | Q(nis2_notifiable="si") | Q(severity="critica")


# ─────────────────────────────────────────────────────────────────────────────
# Letture per i moduli collegati (Reporting, Riesame, Cockpit, Asset, BIA, …).
# Un rischio "valutato" è del registro corrente, applicabile e completato.
# ─────────────────────────────────────────────────────────────────────────────

HIGH_CLASSES = ("high", "critical")
CLASS_LABELS = {
    "very_low": "Very Low", "low": "Low", "medium": "Medium", "high": "High", "critical": "Critical",
}


def evaluated_risks(plant_id=None):
    """Rischi valutati: del sito se `plant_id`, altrimenti di tutta
    l'organizzazione (siti + gruppo). I rischi di gruppo non si sommano ai
    siti che li ereditano, così i totali non contano due volte."""
    qs = (
        RiskAssessment.objects.exclude(cycle__kind="legacy")
        .filter(applicable=True, status="completato")
    )
    return qs.filter(plant_id=plant_id) if plant_id else qs


def class_counts(qs) -> dict:
    """Conteggio per classe e per semaforo (verde/giallo/rosso)."""
    from django.db.models import Count

    by_class = {c: 0 for c in RISK_CLASSES}
    for row in qs.values("current_class").annotate(n=Count("id")):
        if row["current_class"] in by_class:
            by_class[row["current_class"]] = row["n"]
    return {
        **by_class,
        "verde": by_class["very_low"] + by_class["low"],
        "giallo": by_class["medium"],
        "rosso": by_class["high"] + by_class["critical"],
        "total": sum(by_class.values()),
    }


def active_acceptance_risk_ids(qs) -> set:
    from .models import RiskAcceptance

    return set(RiskAcceptance.objects.filter(risk__in=qs, status="active").values_list("risk_id", flat=True))


def untreated_high_risks(qs):
    """High/Critical senza accettazione attiva: oltre la soglia di accettazione
    e non ancora ricondotti (procedura §9.2, §10)."""
    high = qs.filter(current_class__in=HIGH_CLASSES)
    return high.exclude(pk__in=active_acceptance_risk_ids(high))


ACCEPTANCE_WARN_DAYS = 30


def register_attention(plant=None, today=None) -> dict:
    """Cosa richiede di agire nel registro (procedura §9.2, §10, §11.3):
    Critical non accettati (trattamento obbligatorio), High non accettati
    (da trattare o accettare), accettazioni in scadenza, misure in ritardo.
    Solo il registro proprio: i rischi di gruppo ereditati li gestisce il gruppo."""
    import datetime

    from .models import RiskAcceptance, RiskMitigationPlan

    today = today or timezone.localdate()
    risks = register_queryset(plant).filter(applicable=True, status="completato")
    untreated = untreated_high_risks(risks)

    def _ids(qs, field="pk"):
        return sorted({str(x) for x in qs.values_list(field, flat=True)})

    overdue = RiskMitigationPlan.objects.filter(
        assessment__in=register_queryset(plant), completed_at__isnull=True, due_date__lt=today,
    )
    expiring = RiskAcceptance.objects.filter(
        risk__in=risks, status="active",
        expires_on__gte=today, expires_on__lte=today + datetime.timedelta(days=ACCEPTANCE_WARN_DAYS),
    )
    groups = {
        "critical_untreated": _ids(untreated.filter(current_class="critical")),
        "high_untreated": _ids(untreated.filter(current_class="high")),
        "acceptances_expiring": _ids(expiring, "risk_id"),
        "overdue_measures": _ids(overdue, "assessment_id"),
    }
    result = {key: {"count": len(ids), "risk_ids": ids} for key, ids in groups.items()}
    result["overdue_measures"]["measures"] = overdue.count()
    # A parte, non sommati: i rischi di gruppo che riguardano il sito.
    result["inherited"] = inherited_summary(plant) if plant is not None else None
    return result


def inherited_group_risks(plant):
    """Rischi di gruppo valutati che riguardano il sito (`affected_plants`).
    Regola unica: si mostrano nel sito A PARTE e non si sommano ai suoi numeri,
    perché li valuta e li tratta il gruppo (ogni rischio conta una volta sola)."""
    if plant is None:
        return RiskAssessment.objects.none()
    return (
        RiskAssessment.objects.exclude(cycle__kind="legacy")
        .filter(plant__isnull=True, affected_plants=plant, applicable=True, status="completato")
        .distinct()
    )


def inherited_summary(plant) -> dict:
    """Rischi di gruppo che riguardano il sito: totale e High/Critical non accettati."""
    qs = inherited_group_risks(plant)
    untreated = untreated_high_risks(qs)
    return {"count": qs.count(), "untreated_high": untreated.count(),
            "risk_ids": [str(pk) for pk in qs.values_list("pk", flat=True)]}


def register_objectives(plant=None) -> list:
    """Rischi per obiettivo aziendale (procedura §2): la vista che mostra che la
    valutazione parte dagli obiettivi. I numeri sono del registro proprio; per un
    sito i rischi di gruppo ereditati sono indicati a parte (`inherited_*`), non
    sommati. In coda i rischi senza obiettivo."""
    from django.db.models import Q

    from .models import BusinessObjective

    risks = list(
        register_queryset(plant).filter(applicable=True, status="completato")
        .prefetch_related("business_objectives")
    )
    inherited = list(inherited_group_risks(plant).prefetch_related("business_objectives"))
    accepted = active_acceptance_risk_ids(RiskAssessment.objects.filter(pk__in=[r.pk for r in risks + inherited]))
    scope = Q(plant__isnull=True) | (Q(plant=plant) if plant is not None else Q(pk__in=[]))
    rows = []

    def _untreated(linked):
        return [r for r in linked if r.current_class in HIGH_CLASSES and r.pk not in accepted]

    def _row(objective, linked, linked_inherited):
        return {
            "objective": None if objective is None else {
                "id": str(objective.pk), "code": objective.code, "name": objective.name,
                "impact_dimensions": objective.impact_dimensions,
            },
            "count": len(linked),
            "worst_class": worst_class(r.current_class for r in linked),
            "by_class": {c: sum(1 for r in linked if r.current_class == c) for c in RISK_CLASSES},
            "untreated_high": len(_untreated(linked)),
            "risk_ids": [str(r.pk) for r in linked],
            "inherited_count": len(linked_inherited),
            "inherited_untreated_high": len(_untreated(linked_inherited)),
            "inherited_risk_ids": [str(r.pk) for r in linked_inherited],
        }

    def _of(objective, pool):
        return [r for r in pool if objective in r.business_objectives.all()]

    for objective in BusinessObjective.objects.filter(scope, active=True):
        rows.append(_row(objective, _of(objective, risks), _of(objective, inherited)))
    rows.append(_row(None, [r for r in risks if not r.business_objectives.all()],
                     [r for r in inherited if not r.business_objectives.all()]))
    return rows


CONFIDENTIALITY_COVERAGE_LEVELS = ("high", "very_high")


def information_coverage(plant=None) -> list:
    """Classi di informazioni Confidenziali/Segrete e rischi di riservatezza che
    le coprono (VDA ISA 1.3.1/1.3.2): una classe senza rischi valutati con una
    minaccia alla riservatezza è un buco della valutazione."""
    from django.db.models import Q

    from .models import InformationClass

    scope = Q(plant__isnull=True) | (Q(plant=plant) if plant is not None else Q(pk__in=[]))
    classes = InformationClass.objects.filter(scope, confidentiality__in=CONFIDENTIALITY_COVERAGE_LEVELS)
    risks = list(
        register_queryset(plant, include_inherited=plant is not None)
        .filter(applicable=True).select_related("threat").prefetch_related("information_classes")
    )
    out = []
    for ic in classes:
        linked = [r for r in risks if ic in r.information_classes.all() and r.threat and "C" in (r.threat.cia or [])]
        evaluated = [r for r in linked if r.status == "completato"]
        out.append({
            "id": str(ic.pk), "name": ic.name, "confidentiality": ic.confidentiality,
            "plant": str(ic.plant_id) if ic.plant_id else None,
            "state": "evaluated" if evaluated else ("draft" if linked else "missing"),
            "worst_class": worst_class(r.current_class for r in evaluated),
            "risk_ids": [str(r.pk) for r in linked],
        })
    return out


def worst_class(classes) -> str:
    return max((c for c in classes if c), key=class_rank, default="")


# ─────────────────────────────────────────────────────────────────────────────
# Export Excel del registro (procedura §12)
# ─────────────────────────────────────────────────────────────────────────────

def generate_risk_excel(plant=None) -> bytes:
    """Registro corrente del sito (o del gruppo se `plant` è None) in Excel:
    fogli Registro, Piano di trattamento, Accettazioni, Obiettivi aziendali,
    Copertura informazioni, Copertura, Criteri."""
    import io

    from django.utils.translation import get_language
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    from .models import NIS2_ART21_CHOICES, RiskAcceptance, RiskMitigationPlan

    header_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    class_fill = {
        "very_low": "C6EFCE", "low": "E2F0D9", "medium": "FFEB9C", "high": "F8CBAD", "critical": "FFC7CE",
    }

    def sheet(wb, title, headers, first=False):
        ws = wb.active if first else wb.create_sheet()
        ws.title = title
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill, cell.font = header_fill, header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            ws.column_dimensions[cell.column_letter].width = 18
        ws.freeze_panes = "A2"
        return ws

    def name(user):
        return (f"{user.first_name} {user.last_name}".strip() or user.username) if user else ""

    risks = list(
        register_queryset(plant, include_inherited=plant is not None)
        .select_related("plant", "threat", "asset", "supplier", "critical_process", "owner", "treatment_owner")
        .prefetch_related("information_classes", "business_objectives",
                          "existing_measures__control_instance__control")
        .order_by("asset_type", "threat__code")
    )
    art21 = dict(NIS2_ART21_CHOICES)
    wb = Workbook()
    ws = sheet(wb, "Registro", [
        "Registro", "Tipologia", "Codice minaccia", "Minaccia", "Scenario", "Asset / gruppo", "Fornitore",
        "Obiettivi aziendali", "Processo BIA", "Informazioni", "Vulnerabilità", "Conseguenza", "Applicabile",
        "Motivo non applicabile",
        "Misure esistenti", "Probabilità", "Motivazione probabilità",
        "Imp. economico", "Imp. legale", "Imp. cliente", "Imp. reputazionale", "Imp. persone", "Imp. operativo",
        "Impatto", "Motivazione impatto", "Classe matrice", "Override", "Motivazione override", "Classe attuale",
        "Non accettabile", "Trattamento", "Motivazione trattamento", "Prob. attesa", "Imp. atteso", "Classe attesa",
        "Risk Owner", "Responsabile trattamento", "Scadenza piano", "NIS2 in perimetro", "Art. 21 NIS2",
        "Sistemi impattati", "Possibile incidente significativo", "Stato", "Valutato il",
    ], first=True)
    for row, r in enumerate(risks, 2):
        measures = "; ".join(
            f"{(m.control_instance.control.external_id + ' ') if m.control_instance else ''}{m.description} ({m.effectiveness})"
            for m in r.existing_measures.all()
        )
        values = [
            r.plant.name if r.plant else "Gruppo", r.asset_type, r.threat.code if r.threat else "",
            r.threat.get_title((get_language() or "en")[:2]) if r.threat else "", risk_label(r),
            r.asset.name if r.asset else r.asset_group_label, r.supplier.name if r.supplier else "",
            ", ".join(bo.name for bo in r.business_objectives.all()),
            r.critical_process.name if r.critical_process else "",
            ", ".join(ic.name for ic in r.information_classes.all()), r.vulnerability, r.consequence,
            "Sì" if r.applicable else "No", r.not_applicable_reason, measures,
            r.probability, r.probability_rationale,
            r.impact_economic, r.impact_legal, r.impact_customer, r.impact_reputational, r.impact_people,
            r.impact_operational, r.impact, r.impact_rationale, CLASS_LABELS.get(r.matrix_class, ""),
            r.class_override or "", r.override_rationale, CLASS_LABELS.get(r.current_class, ""),
            "Sì" if r.legal_or_contract_violation else "", r.treatment, r.treatment_rationale,
            r.expected_probability, r.expected_impact, CLASS_LABELS.get(r.expected_class, ""),
            name(r.owner), mixed_owner_name(r.treatment_owner, r.treatment_owner_external) or "",
            r.plan_due_date, "Sì" if r.nis2_in_scope else "No", art21.get(r.nis2_art21_category, ""),
            r.impacted_systems, "Sì" if r.significant_incident_potential else "No", r.status,
            r.assessed_at.date() if r.assessed_at else None,
        ]
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        cls_col = 28
        if r.current_class in class_fill:
            ws.cell(row=row, column=cls_col).fill = PatternFill("solid", fgColor=class_fill[r.current_class])

    ws = sheet(wb, "Piano di trattamento", [
        "Rischio", "Classe attuale", "Classe attesa", "Misura", "Effetto atteso", "Controllo",
        "Responsabile", "Scadenza", "Completata il", "Verificata il", "Nota verifica",
    ])
    plans = RiskMitigationPlan.objects.filter(assessment__in=risks).select_related(
        "assessment", "assessment__threat", "owner", "control_instance__control",
    ).order_by("due_date")
    for row, p in enumerate(plans, 2):
        for col, value in enumerate([
            risk_label(p.assessment), CLASS_LABELS.get(p.assessment.current_class, ""),
            CLASS_LABELS.get(p.assessment.expected_class, ""), p.action, p.expected_effect,
            p.control_instance.control.external_id if p.control_instance else "",
            mixed_owner_name(p.owner, p.owner_external) or "", p.due_date,
            p.completed_at.date() if p.completed_at else None,
            p.verified_at.date() if p.verified_at else None, p.verification_note,
        ], 1):
            ws.cell(row=row, column=col, value=value)

    ws = sheet(wb, "Accettazioni", [
        "Rischio", "Classe", "Stato", "Ruoli richiesti", "Firme", "Organo", "Delibera", "Parere",
        "Motivazione", "Scadenza", "Attiva dal",
    ])
    accs = RiskAcceptance.objects.filter(risk__in=risks).select_related("risk", "risk__threat", "body").order_by("-created_at")
    for row, a in enumerate(accs, 2):
        for col, value in enumerate([
            risk_label(a.risk), CLASS_LABELS.get(a.risk_class, ""), a.status, ", ".join(a.required_roles),
            ", ".join(s["role"] for s in a.signatures), a.body.name if a.body else "", a.body_resolution_ref,
            a.upper_opinion, a.rationale, a.expires_on, a.activated_at.date() if a.activated_at else None,
        ], 1):
            ws.cell(row=row, column=col, value=value)

    ws = sheet(wb, "Obiettivi aziendali", [
        "Obiettivo", "Rischi valutati", "Classe peggiore", "High/Critical non accettati",
        "Critical", "High", "Medium", "Low", "Very Low",
        "Rischi di gruppo ereditati (non sommati)", "di cui High/Critical non accettati",
    ])
    for row, item in enumerate(register_objectives(plant), 2):
        bc = item["by_class"]
        for col, value in enumerate([
            item["objective"]["name"] if item["objective"] else "(nessun obiettivo indicato)",
            item["count"], CLASS_LABELS.get(item["worst_class"], ""), item["untreated_high"],
            bc["critical"], bc["high"], bc["medium"], bc["low"], bc["very_low"],
            item["inherited_count"], item["inherited_untreated_high"],
        ], 1):
            ws.cell(row=row, column=col, value=value)
    ws = sheet(wb, "Copertura informazioni", ["Classe di informazioni", "Riservatezza", "Stato", "Classe peggiore"])
    for row, item in enumerate(information_coverage(plant), 2):
        for col, value in enumerate([
            item["name"], item["confidentiality"], COVERAGE_STATE_LABELS.get(item["state"], item["state"]),
            CLASS_LABELS.get(item["worst_class"], ""),
        ], 1):
            ws.cell(row=row, column=col, value=value)
    ws = sheet(wb, "Copertura", ["Tipologia", "Codice minaccia", "Stato", "Classe peggiore"])
    for row, pair in enumerate(register_coverage(plant)["pairs"], 2):
        for col, value in enumerate([
            pair["asset_type"], pair["threat_code"], COVERAGE_STATE_LABELS.get(pair["state"], pair["state"]),
            CLASS_LABELS.get(pair["worst_class"], ""),
        ], 1):
            ws.cell(row=row, column=col, value=value)

    ws = sheet(wb, "Criteri", ["Probabilità \\ Impatto", "1", "2", "3", "4", "5"])
    for row, p in enumerate(range(5, 0, -1), 2):
        ws.cell(row=row, column=1, value=p)
        for i in range(1, 6):
            cls = risk_class(p, i)
            cell = ws.cell(row=row, column=i + 1, value=CLASS_LABELS[cls])
            cell.fill = PatternFill("solid", fgColor=class_fill[cls])
    policy = resolve_policy(plant)
    ws.cell(row=8, column=1, value="Soglie economiche (€, limite inferiore del livello)")
    for offset, level in enumerate(("2", "3", "4", "5")):
        ws.cell(row=9 + offset, column=1, value=f"Livello {level}")
        ws.cell(row=9 + offset, column=2, value=policy["economic_thresholds"][level])
    ws.cell(row=14, column=1, value="Modello di governo")
    ws.cell(row=14, column=2, value=policy["preset"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generate_cycle_excel(cycle) -> bytes:
    """Fotografia congelata di una valutazione approvata (procedura §11.5):
    registro, copertura e criteri in vigore al momento dell'approvazione."""
    import io

    from django.utils.translation import gettext as _
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    if not cycle.snapshot:
        raise _err(_("La valutazione non ha una fotografia: si esporta solo una valutazione approvata."))
    snap = cycle.snapshot
    fill = PatternFill("solid", fgColor="1E3A5F")
    font = Font(color="FFFFFF", bold=True, size=10)

    def header(ws, cols):
        for i, col in enumerate(cols, 1):
            cell = ws.cell(row=1, column=i, value=col)
            cell.fill, cell.font = fill, font
            ws.column_dimensions[cell.column_letter].width = 18
        ws.freeze_panes = "A2"

    wb = Workbook()
    ws = wb.active
    ws.title = "Valutazione"
    rows = [
        ("Registro", cycle.plant.name if cycle.plant else "Gruppo"),
        ("Tipo", cycle.get_kind_display()),
        ("Avviata il", cycle.started_at.date() if cycle.started_at else None),
        ("Approvata il", cycle.approved_at.date() if cycle.approved_at else None),
        ("Organo", cycle.approved_by_body.name if cycle.approved_by_body else ""),
        ("Recepimento della società", cycle.local_adoption_ref),
        ("Motivo (revisione straordinaria)", cycle.trigger_reason),
        ("Copertura", f"{snap.get('coverage', {}).get('closed', 0)}/{snap.get('coverage', {}).get('total', 0)}"),
        ("Modello di governo", snap.get("policy", {}).get("preset", "")),
    ]
    for r, (k, v) in enumerate(rows, 1):
        ws.cell(row=r, column=1, value=k).font = Font(bold=True)
        ws.cell(row=r, column=2, value=v)
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 40

    ws = wb.create_sheet("Registro")
    cols = ["Tipologia", "Minaccia", "Scenario", "Obiettivi aziendali", "Informazioni", "Applicabile",
            "Motivo non applicabile", "Asset / gruppo", "Fornitore", "Processo", "Probabilità", "Impatto", *[f"Imp. {d}" for d in IMPACT_DIMENSIONS],
            "Classe attuale", "Classe attesa", "Trattamento", "Misure (completate/verificate)",
            "Accettazione", "Siti che lo ereditano"]
    header(ws, cols)
    for r, item in enumerate(snap.get("risks", []), 2):
        plans = item.get("plans", [])
        acc = item.get("acceptance")
        values = [
            item.get("asset_type"), item.get("threat"), item.get("name"),
            ", ".join(item.get("business_objectives") or []), ", ".join(item.get("information_classes") or []),
            "Sì" if item.get("applicable") else "No", item.get("not_applicable_reason"), item.get("asset"),
            item.get("supplier"), item.get("process"), item.get("probability"), item.get("impact"),
            *[(item.get("impacts") or {}).get(d) for d in IMPACT_DIMENSIONS],
            CLASS_LABELS.get(item.get("current_class"), ""), CLASS_LABELS.get(item.get("expected_class"), ""),
            item.get("treatment"),
            f"{len(plans)} ({sum(1 for p in plans if p.get('completed'))}/{sum(1 for p in plans if p.get('verified'))})",
            f"{CLASS_LABELS.get(acc['class'], '')} fino al {acc['expires_on']}" if acc else "",
            len(item.get("affected_plants") or []) or "",
        ]
        for c, v in enumerate(values, 1):
            ws.cell(row=r, column=c, value=v)

    if snap.get("objectives"):
        ws = wb.create_sheet("Obiettivi aziendali")
        header(ws, ["Obiettivo", "Rischi valutati", "Classe peggiore", "High/Critical non accettati"])
        for r, item in enumerate(snap["objectives"], 2):
            for c, v in enumerate([
                (item.get("objective") or {}).get("name") or "(nessun obiettivo indicato)", item.get("count"),
                CLASS_LABELS.get(item.get("worst_class"), ""), item.get("untreated_high"),
            ], 1):
                ws.cell(row=r, column=c, value=v)

    ws = wb.create_sheet("Criteri")
    policy = snap.get("policy", {})
    header(ws, ["Classe", "Ruoli che firmano", "Livello", "Delibera organo", "Parere CISO", "Validità (mesi)"])
    for r, cls in enumerate(reversed(RISK_CLASSES), 2):
        rule = (policy.get("acceptance_matrix") or {}).get(cls, {})
        for c, v in enumerate([
            CLASS_LABELS[cls], ", ".join(rule.get("roles", [])), rule.get("scope", ""),
            "Sì" if rule.get("requires_body") else "No", (policy.get("upper_opinion") or {}).get(cls, ""),
            (policy.get("acceptance_max_months") or {}).get(cls, ""),
        ], 1):
            ws.cell(row=r, column=c, value=v)
    thresholds = policy.get("economic_thresholds") or {}
    ws.cell(row=9, column=1, value="Soglie economiche (€, limite inferiore)").font = Font(bold=True)
    for offset, level in enumerate(("2", "3", "4", "5")):
        ws.cell(row=10 + offset, column=1, value=f"Livello {level}")
        ws.cell(row=10 + offset, column=2, value=thresholds.get(level))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def legacy_register_rows(plant) -> list:
    """Registro del metodo superato (valori congelati), per pacchetti audit ed export."""
    rows = []
    risks = RiskAssessment.objects.filter(cycle__kind="legacy", plant=plant).order_by("created_at")
    for r in risks:
        s = r.legacy_snapshot or {}
        rows.append({
            "name": risk_label(r),
            "assessment_type": s.get("assessment_type", ""),
            "threat_category": s.get("threat_category", ""),
            "probability": s.get("probability"),
            "impact": s.get("impact"),
            "score": s.get("score"),
            "inherent_score": s.get("inherent_score"),
            "treatment": s.get("treatment", ""),
            "cause": s.get("cause", ""),
            "consequence": s.get("consequence", ""),
            "risk_accepted_formally": s.get("risk_accepted_formally"),
            "risk_acceptance_note": s.get("risk_acceptance_note", ""),
            "risk_acceptance_expiry": s.get("risk_acceptance_expiry", ""),
            "assessed_at": s.get("assessed_at", ""),
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Supporto IA (M20): contesto, criteri della procedura, validazione delle
# proposte e controlli di coerenza. Le chiamate al modello stanno in
# ai_engine.tasks_ai; qui solo regole deterministiche. Nessuna proposta IA è
# applicata senza conferma dell'utente (regola 9).
# ─────────────────────────────────────────────────────────────────────────────

# Criteri della procedura di risk management (§7) usati nei prompt: stessi testi
# delle scale mostrate nella scheda del rischio.
PROCEDURE_CRITERIA = {
    "probability": {
        "5": "frequenza: più di 1 volta l'anno | FER: vulnerabilità non presidiate o controlli non efficaci",
        "4": "frequenza: 1 volta ogni 1–2 anni | FER: controlli con lacune o non del tutto efficaci",
        "3": "frequenza: 1 volta ogni 2–4 anni | FER: vulnerabilità sfruttabili solo da esperti o da eventi naturali importanti",
        "2": "frequenza: 1 volta ogni 4–10 anni | FER: serve un attacco mirato molto motivato o un evento eccezionale",
        "1": "frequenza: meno di 1 volta ogni 10 anni | FER: controlli multipli e verificati, nessun agente credibile",
    },
    "legal": {
        "5": "sanzioni penali per amministratori; sanzioni NIS2 o GDPR della fascia massima; provvedimenti interdittivi",
        "4": "sanzioni penali per dipendenti; sanzioni amministrative rilevanti",
        "3": "sanzioni civili rilevanti; sanzioni amministrative minori o diffide",
        "2": "procedimento legale ordinario; contenziosi routinari",
        "1": "nessuna conseguenza legale",
    },
    "customer": {
        "5": "perdita o sospensione della label TISAX; perdita di un cliente OEM; fermo linea presso il cliente",
        "4": "penali contrattuali rilevanti; escalation formale; violazione di NDA su informazioni high o very high",
        "3": "reclamo formale del cliente; ritardi recuperati con costi straordinari",
        "2": "segnalazione informale del cliente, senza penali",
        "1": "nessun effetto sul cliente",
    },
    "reputational": {
        "5": "notizia su media nazionali o internazionali; fiducia compromessa in modo duraturo",
        "4": "danno visibile a clienti e settore",
        "3": "danno noto ad alcuni clienti o partner, senza effetti duraturi",
        "2": "danno lieve, limitato all'interno o a pochi interlocutori",
        "1": "nessun effetto",
    },
    "people": {
        "5": "decessi o infortuni con danni permanenti a più persone",
        "4": "decesso o infortunio con danni permanenti a una persona",
        "3": "lieve infortunio di una o più persone",
        "2": "nessun infortunio",
        "1": "nessun effetto",
    },
    "operational": {
        "5": "processo critico fermo oltre l'MTPD; consegne bloccate oltre 24 ore; funzioni interne ferme oltre 2 giorni",
        "4": "interruzione oltre l'RTO ma entro l'MTPD; consegne con forti ritardi; 31–50% delle funzioni ferme",
        "3": "disagi nelle consegne entro l'RTO; 11–30% delle funzioni ferme",
        "2": "1–10% delle funzioni ferme; nessun effetto sulle consegne",
        "1": "nessun effetto apprezzabile",
    },
}

AI_TREATMENTS = ("mitigare", "evitare", "trasferire", "accettare")
AI_EFFECTS = ("probabilita", "impatto", "entrambi")


def economic_criteria(plant) -> dict:
    """Fasce dell'impatto economico (€) dalla policy del registro."""
    th = resolve_policy(plant)["economic_thresholds"]
    return {
        "5": f"oltre {th['5']} €", "4": f"da {th['4']} a {th['5']} €", "3": f"da {th['3']} a {th['4']} €",
        "2": f"da {th['2']} a {th['3']} €", "1": f"meno di {th['2']} €",
    }


def risk_ai_context(risk, lang: str = "it") -> dict:
    """Dati del rischio per la bozza IA: solo ciò che il programma sa già.
    Le persone non compaiono (owner esclusi); il resto passa dal Sanitizer."""
    threat = risk.threat
    process = risk.critical_process
    return {
        "registro": risk.plant.name if risk.plant else "gruppo (servizi condivisi)",
        "paese": risk.plant.country if risk.plant else None,
        "nis2": bool(risk.nis2_in_scope),
        "tipologia_asset": risk.asset_type,
        "minaccia": ({"codice": threat.code, "titolo": threat.get_title(lang),
                      "descrizione": threat.tr("description", lang), "cia": threat.cia} if threat else None),
        "asset": ({"nome": risk.asset.name, "criticita": getattr(risk.asset, "criticality", None)}
                  if risk.asset_id else (risk.asset_group_label or None)),
        "fornitore": risk.supplier.name if risk.supplier_id else None,
        "processo_bia": ({
            "nome": process.name, "criticita": process.criticality, "rto_ore": process.rto_target_hours,
            "mtpd_ore": process.mtpd_hours,
            "costo_fermo_ora_eur": float(process.downtime_cost_hour) if process.downtime_cost_hour else None,
        } if process else None),
        "informazioni": [{"nome": ic.name, "riservatezza": ic.confidentiality, "integrita": ic.integrity,
                          "disponibilita": ic.availability} for ic in risk.information_classes.all()],
        "obiettivi_aziendali": [{"nome": bo.name, "dimensioni": bo.impact_dimensions}
                                for bo in risk.business_objectives.all()],
        "misure_esistenti": [
            {"descrizione": m.description, "efficacia": m.effectiveness,
             "controllo": (f"{m.control_instance.control.external_id} ({m.control_instance.status})"
                           if m.control_instance_id else None)}
            for m in risk.existing_measures.select_related("control_instance__control")
        ],
        "testi_attuali": {"vulnerabilita": risk.vulnerability, "conseguenza": risk.consequence},
    }


def _clip(value, limit: int = 1200) -> str:
    return str(value or "").strip()[:limit]


def _level(value):
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    return v if 1 <= v <= 5 else None


def _ai_method(value) -> str:
    """Metodo della probabilità: "frequenza" o "fer" (anche in maiuscolo o con spazi)."""
    v = str(value or "").strip().lower()
    return v if v in ("frequenza", "fer") else ""


def validate_ai_draft(data: dict) -> dict:
    """Proposta di valutazione ripulita: solo campi noti, livelli 1–5, valori
    ammessi. La classe NON arriva dall'IA: la calcola la matrice."""
    data = data if isinstance(data, dict) else {}
    out = {
        "vulnerability": _clip(data.get("vulnerability")),
        "consequence": _clip(data.get("consequence")),
        "probability": _level(data.get("probability")),
        "probability_method": _ai_method(data.get("probability_method")),
        "probability_rationale": _clip(data.get("probability_rationale")),
        "impact_rationale": _clip(data.get("impact_rationale")),
        "treatment": data.get("treatment") if data.get("treatment") in AI_TREATMENTS else "",
        "treatment_rationale": _clip(data.get("treatment_rationale")),
        "expected_probability": _level(data.get("expected_probability")),
        "expected_impact": _level(data.get("expected_impact")),
    }
    impacts = data.get("impacts") if isinstance(data.get("impacts"), dict) else {}
    for dim in IMPACT_DIMENSIONS:
        out[f"impact_{dim}"] = _level(impacts.get(dim))
    return {k: v for k, v in out.items() if v not in ("", None)}


def ai_control_candidates(risk, limit: int = 40) -> list:
    """Controlli del sito che una misura può richiamare: prima quelli non conformi."""
    from apps.controls.models import ControlInstance

    if risk.plant_id is None:
        return []
    order = {"gap": 0, "parziale": 1, "non_valutato": 2, "compliant": 3}
    rows = list(
        ControlInstance.objects.filter(plant_id=risk.plant_id).exclude(status="na")
        .select_related("control")
    )
    rows.sort(key=lambda ci: (order.get(ci.status, 9), ci.control.external_id))
    return rows[:limit]


def validate_ai_measures(items, risk, candidates: list) -> list:
    """Misure proposte ripulite: testo, effetto ammesso, scadenza entro il
    termine della classe (§9.2), controllo solo fra quelli del sito."""
    import datetime

    months = (treatment_rule(risk.current_class) or {}).get("months", 12)
    limit_days = 30 * months
    today = timezone.localdate()
    out = []
    for item in (items if isinstance(items, list) else [])[:5]:
        if not isinstance(item, dict) or not _clip(item.get("action"), 500):
            continue
        try:
            weeks = max(1, int(item.get("weeks") or 0))
        except (TypeError, ValueError):
            weeks = 4
        days = min(weeks * 7, limit_days)
        idx = item.get("control")
        control = candidates[idx - 1] if isinstance(idx, int) and 1 <= idx <= len(candidates) else None
        out.append({
            "action": _clip(item.get("action"), 500),
            "expected_effect": item.get("expected_effect") if item.get("expected_effect") in AI_EFFECTS else "",
            "due_date": (today + datetime.timedelta(days=days)).isoformat(),
            "control_instance": str(control.pk) if control else None,
            "control_label": f"{control.control.external_id} — {control.control.get_title()}" if control else None,
            "rationale": _clip(item.get("rationale"), 400),
        })
    return out


# ── Identificazione dei rischi dai buchi di copertura (§6.5) ────────────────

# Coppie proposte per chiamata: con la bozza completa per ognuna, oltre questo
# numero la risposta del modello rischia di essere troncata.
AI_IDENTIFY_BATCH = 6
# Tipologie della copertura → tipi di asset dell'inventario M04.
_COVERAGE_ASSET_KINDS = {"IT": ("IT", "SW"), "OT": ("OT", "FAC"), "SEDE": ("FAC",)}


def ai_identification_threats(plant, asset_type: str) -> list:
    """Minacce del catalogo ancora scoperte per la tipologia nel registro."""
    from .models import ThreatCatalogEntry

    missing = [p["threat_id"] for p in register_coverage(plant)["pairs"]
               if p["asset_type"] == asset_type and p["state"] == "missing"]
    return list(ThreatCatalogEntry.objects.filter(pk__in=missing).order_by("code"))


def ai_link_candidates(plant) -> dict:
    """Processi BIA, obiettivi aziendali e classi di informazioni che una
    proposta IA può richiamare per numero: solo quelli del registro o di gruppo."""
    from apps.bia.models import CriticalProcess
    from django.db.models import Case, IntegerField, Q, Value, When

    from .models import BusinessObjective, InformationClass

    processes = list(CriticalProcess.objects.filter(plant=plant).order_by("-criticality", "name")[:15]) \
        if plant is not None else []
    objectives = list(
        BusinessObjective.objects.filter(Q(plant__isnull=True) | Q(plant=plant), active=True)
        .order_by("order", "name")
    )
    rank = Case(*(When(confidentiality=lvl, then=Value(i)) for i, lvl in
                  enumerate(("very_high", "high", "normal", "low"))), output_field=IntegerField())
    information = list(
        InformationClass.objects.filter(Q(plant__isnull=True) | Q(plant=plant))
        .annotate(_rank=rank).order_by("_rank", "name")[:30]
    )
    return {"processes": processes, "objectives": objectives, "information": information}


def ai_link_payload(links: dict) -> dict:
    """Le stesse liste, numerate, per il prompt."""
    return {
        "processi_bia": [
            {"n": i, "nome": p.name, "criticita": p.criticality, "rto_ore": p.rto_target_hours,
             "mtpd_ore": p.mtpd_hours}
            for i, p in enumerate(links["processes"], start=1)
        ],
        "obiettivi_aziendali": [
            {"n": i, "nome": o.name, "descrizione": _clip(o.description, 300), "dimensioni_impatto": o.impact_dimensions}
            for i, o in enumerate(links["objectives"], start=1)
        ],
        "classi_informazioni": [
            {"n": i, "nome": ic.name, "riservatezza": ic.confidentiality, "integrita": ic.integrity,
             "disponibilita": ic.availability}
            for i, ic in enumerate(links["information"], start=1)
        ],
    }


def ai_link_names(links: dict) -> dict:
    """id → nome, per mostrare nell'interfaccia i riferimenti proposti."""
    return {
        "processes": {str(p.pk): p.name for p in links["processes"]},
        "objectives": {str(o.pk): o.name for o in links["objectives"]},
        "information": {str(ic.pk): ic.name for ic in links["information"]},
    }


def _ai_indexes(value) -> list:
    """Numeri di elenco proposti dal modello: interi o stringhe numeriche, senza ripetizioni."""
    out = []
    for v in value if isinstance(value, list) else [value]:
        try:
            n = int(str(v).strip())
        except (TypeError, ValueError):
            continue
        if n not in out:
            out.append(n)
    return out


def validate_ai_links(data: dict, links: dict) -> dict:
    """Riferimenti proposti ripuliti: solo numeri fra quelli forniti nel prompt."""
    def pick(key, items, limit):
        return [str(items[n - 1].pk) for n in _ai_indexes(data.get(key)) if 1 <= n <= len(items)][:limit]

    process = pick("process", links["processes"], 1)
    return {
        "critical_process": process[0] if process else None,
        "business_objectives": pick("objectives", links["objectives"], 3),
        "information_classes": pick("information", links["information"], 8),
    }


def risk_identification_context(plant, asset_type: str, links: dict, lang: str = "it") -> dict:
    """Quello che il programma sa del registro per decidere quali minacce si
    applicano. Solo dati aggregati o di inventario: nessuna persona."""
    import datetime

    from django.db.models import Count, Q

    from apps.assets.models import Asset
    from apps.incidents.models import Incident
    from apps.suppliers.models import Supplier

    ctx = {
        "registro": plant.name if plant else "gruppo (servizi condivisi)",
        "paese": plant.country if plant else None,
        "nis2": bool(plant and plant.is_nis2_subject),
        "ha_ot": bool(plant and plant.has_ot),
        "tipologia_asset": asset_type,
        "tipologie_presenti": asset_types_present(plant),
        **ai_link_payload(links),
    }
    kinds = _COVERAGE_ASSET_KINDS.get(asset_type)
    if kinds and plant is not None:
        assets = Asset.objects.filter(plant=plant, asset_type__in=kinds)
        ctx["asset"] = {
            "totale": assets.count(),
            "piu_critici": [{"nome": a.name, "criticita": a.criticality}
                            for a in assets.order_by("-criticality", "name")[:15]],
        }
    if asset_type == "FORNITORI":
        suppliers = Supplier.objects.filter(status="attivo")
        if plant is not None:
            suppliers = suppliers.filter(Q(plants=plant) | Q(plants__isnull=True)).distinct()
        ctx["fornitori"] = {
            "attivi": suppliers.count(),
            "per_livello_rischio": dict(
                suppliers.order_by().values_list("risk_level").annotate(n=Count("pk", distinct=True))
            ),
        }
    if plant is not None:
        since = timezone.now() - datetime.timedelta(days=730)
        ctx["incidenti_24_mesi"] = [
            {"categoria": row["incident_category"] or "non classificato", "gravita": row["severity"], "numero": row["n"]}
            for row in Incident.objects.filter(plant=plant, detected_at__gte=since).order_by()
            .values("incident_category", "severity").annotate(n=Count("pk"))
        ]
    return ctx


def validate_ai_identification(items, threats: list, links: dict) -> list:
    """Proposte ripulite, una per minaccia scoperta: applicabile con la bozza
    della valutazione, oppure non applicabile con il motivo. Solo minacce della
    richiesta; processi e obiettivi solo fra quelli forniti."""
    by_code = {t.code: t for t in threats}
    out, seen = [], set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        threat = by_code.get(str(item.get("threat") or "").strip())
        if threat is None or threat.pk in seen:
            continue
        seen.add(threat.pk)
        applicable = item.get("applicable") is not False
        row = {"threat_id": str(threat.pk), "threat_code": threat.code, "applicable": applicable,
               "reason": _clip(item.get("reason"), 600)}
        if applicable:
            row["proposal"] = validate_ai_draft(item)
            row.update(validate_ai_links(item, links))
        elif not row["reason"]:
            continue  # "non applicabile" senza motivo non si può dichiarare (§6.5)
        out.append(row)
    return out


_AI_IDENTIFY_FIELDS = (
    "vulnerability", "consequence", "probability", "probability_method", "probability_rationale",
    *(f"impact_{d}" for d in IMPACT_DIMENSIONS), "impact_rationale",
    "treatment", "treatment_rationale", "expected_probability", "expected_impact",
)


def apply_ai_identification(user, plant, asset_type: str, items: list) -> dict:
    """Registra le proposte di identificazione scelte dall'utente: rischi in
    bozza nel ciclo in corso o coppie non applicabili. Le coppie nel frattempo
    coperte si saltano; il resto passa dalle stesse regole dell'inserimento a
    mano (create_risk / mark_not_applicable)."""
    from apps.bia.models import CriticalProcess
    from django.utils.translation import gettext as _

    from core.audit import log_action

    from .models import BusinessObjective, InformationClass

    require_register_write(user, plant)
    cycle = _require_evaluation_cycle(plant)
    if not isinstance(items, list) or not items:
        raise _err(_("Seleziona almeno una proposta."))
    open_threats = {str(t.pk): t for t in ai_identification_threats(plant, asset_type)}
    created, not_applicable, skipped = [], 0, 0
    with transaction.atomic():
        for item in items:
            threat = open_threats.pop(str((item or {}).get("threat_id")), None) if isinstance(item, dict) else None
            if threat is None:
                skipped += 1
                continue
            if item.get("applicable") is False:
                mark_not_applicable(user, plant, asset_type, threat, str(item.get("reason") or ""))
                not_applicable += 1
                continue
            proposal = item.get("proposal") if isinstance(item.get("proposal"), dict) else {}
            data = {k: proposal[k] for k in _AI_IDENTIFY_FIELDS if k in proposal}
            data = validate_ai_draft({**data, "impacts": {d: data.pop(f"impact_{d}", None) for d in IMPACT_DIMENSIONS}})
            data.update({"asset_type": asset_type, "threat": threat})
            if item.get("critical_process") and plant is not None:
                data["critical_process"] = CriticalProcess.objects.filter(
                    pk=item["critical_process"], plant=plant).first()
            objective_ids = [str(i) for i in item.get("business_objectives") or []][:3]
            if objective_ids:
                data["business_objectives"] = list(BusinessObjective.objects.filter(pk__in=objective_ids, active=True))
            info_ids = [str(i) for i in item.get("information_classes") or []][:8]
            if info_ids:
                data["information_classes"] = list(InformationClass.objects.filter(pk__in=info_ids))
            created.append(create_risk(user, plant, data))
        log_action(
            user=user, action_code="risk.ai.identification_applied", level="L2", entity=cycle,
            payload={"asset_type": asset_type, "created": len(created), "not_applicable": not_applicable,
                     "skipped": skipped},
        )
    return {"created": [str(r.pk) for r in created], "not_applicable": not_applicable, "skipped": skipped}


def register_consistency_checks(plant=None) -> list:
    """Controlli di coerenza deterministici del registro proprio (gratuiti e
    ripetibili), prima dell'invio in approvazione. Ritorna codici + parametri:
    i testi li compone l'interfaccia nella lingua dell'utente."""
    risks = list(
        register_queryset(plant).filter(applicable=True)
        .select_related("threat").prefetch_related("information_classes", "business_objectives", "mitigation_plans")
    )
    findings = []

    def add(code, risk, severity="warning", **params):
        findings.append({"code": code, "severity": severity, "risk_id": str(risk.pk),
                         "risk_name": risk_label(risk), "params": params})

    for r in risks:
        valued = {d for d in IMPACT_DIMENSIONS if getattr(r, f"impact_{d}")}
        if r.threat and "C" in (r.threat.cia or []) and not r.information_classes.all():
            add("confidentiality_without_information", r)
        objectives = list(r.business_objectives.all())
        if objectives and valued and not any(set(bo.impact_dimensions) & valued for bo in objectives):
            add("objectives_not_matching_impact", r, objectives=", ".join(bo.name for bo in objectives))
        if r.status == "completato" and r.current_class in HIGH_CLASSES \
                and r.treatment in ("mitigare", "evitare", "trasferire") and not r.mitigation_plans.all():
            add("high_without_plan", r, severity="error")
        for field in ("probability_rationale", "impact_rationale"):
            if getattr(r, field) and len(getattr(r, field).strip()) < 25:
                add("rationale_too_short", r, field=field)
        if r.treatment in ("mitigare", "evitare", "trasferire") and r.expected_class and r.current_class \
                and class_rank(r.expected_class) >= class_rank(r.current_class):
            add("expected_not_lower", r)
    groups: dict = {}
    for r in risks:
        if r.threat_id and r.impact:
            groups.setdefault((r.threat_id, r.asset_type), []).append(r)
    for same in groups.values():
        if len(same) > 1:
            low, high = min(same, key=lambda x: x.impact), max(same, key=lambda x: x.impact)
            if high.impact - low.impact >= 3:
                add("impact_spread", high, other=risk_label(low), low=low.impact, high=high.impact)
    rank = {"error": 0, "warning": 1}
    findings.sort(key=lambda f: (rank[f["severity"]], f["code"], f["risk_name"]))
    return findings


def register_ai_digest(plant=None) -> dict:
    """Numeri del registro per la sintesi IA destinata all'organo: solo le
    funzioni uniche già usate da Reporting e riesame."""
    risks = evaluated_risks(plant.pk if plant else None) if plant is not None else register_queryset(None).filter(
        applicable=True, status="completato")
    from .models import RiskAcceptance, RiskMitigationPlan

    today = timezone.localdate()
    top = sorted(untreated_high_risks(risks).select_related("threat"),
                 key=lambda r: (class_rank(r.current_class), r.impact or 0), reverse=True)[:8]
    return {
        "registro": plant.name if plant else "gruppo",
        "per_classe": class_counts(risks),
        "per_obiettivo": [
            {"obiettivo": (o["objective"] or {}).get("name") or "senza obiettivo", "rischi": o["count"],
             "classe_peggiore": o["worst_class"], "high_critical_non_accettati": o["untreated_high"]}
            for o in register_objectives(plant)
        ],
        "principali_non_accettati": [{"rischio": risk_label(r), "classe": r.current_class,
                                      "trattamento": r.treatment} for r in top],
        "accettazioni_attive": RiskAcceptance.objects.filter(risk__in=risks, status="active").count(),
        "misure_in_ritardo": RiskMitigationPlan.objects.filter(
            assessment__in=risks, completed_at__isnull=True, due_date__lt=today).count(),
        "copertura": {k: v for k, v in register_coverage(plant).items() if k != "pairs"},
        "informazioni_scoperte": sum(1 for i in information_coverage(plant) if i["state"] == "missing"),
        "rischi_di_gruppo_che_riguardano_il_sito": (
            {k: v for k, v in inherited_summary(plant).items() if k != "risk_ids"} if plant is not None else None
        ),
    }
