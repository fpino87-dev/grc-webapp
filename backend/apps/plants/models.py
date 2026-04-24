from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import BaseModel

EU_COUNTRIES = [
    ("AT", "Austria"),
    ("BE", "Belgio"),
    ("BG", "Bulgaria"),
    ("CY", "Cipro"),
    ("CZ", "Repubblica Ceca"),
    ("DE", "Germania"),
    ("DK", "Danimarca"),
    ("EE", "Estonia"),
    ("ES", "Spagna"),
    ("FI", "Finlandia"),
    ("FR", "Francia"),
    ("GR", "Grecia"),
    ("HR", "Croazia"),
    ("HU", "Ungheria"),
    ("IE", "Irlanda"),
    ("IT", "Italia"),
    ("LT", "Lituania"),
    ("LU", "Lussemburgo"),
    ("LV", "Lettonia"),
    ("MT", "Malta"),
    ("NL", "Paesi Bassi"),
    ("PL", "Polonia"),
    ("PT", "Portogallo"),
    ("RO", "Romania"),
    ("SE", "Svezia"),
    ("SI", "Slovenia"),
    ("SK", "Slovacchia"),
    # Non UE — non soggetti NIS2
    ("GB", "Regno Unito"),
    ("NO", "Norvegia"),
    ("CH", "Svizzera"),
    ("TR", "Turchia"),
    ("US", "Stati Uniti"),
    ("JP", "Giappone"),
    ("CN", "Cina"),
    ("OTHER", "Altro"),
]

CSIRT_BY_COUNTRY = {
    "IT": {
        "name": "ACN — Agenzia Cybersicurezza Nazionale",
        "portal": "https://www.acn.gov.it/portale/nis/notifica-incidenti",
        "email": "cert@acn.gov.it",
        "country": "Italia",
    },
    "DE": {
        "name": "BSI — Bundesamt fur Sicherheit in der Informationstechnik",
        "portal": "https://www.bsi.bund.de/EN/Topics/KRITIS/NIS2/nis2_node.html",
        "email": "nis2@bsi.bund.de",
        "country": "Germania",
    },
    "FR": {
        "name": "ANSSI — Agence Nationale de la Securite des Systemes d'Information",
        "portal": "https://www.ssi.gouv.fr/en/",
        "email": "cert-fr@ssi.gouv.fr",
        "country": "Francia",
    },
    "PL": {
        "name": "CERT Polska / NASK",
        "portal": "https://incydent.cert.pl/",
        "email": "incydent@cert.pl",
        "country": "Polonia",
    },
    "BE": {
        "name": "CCN / CERT.be",
        "portal": "https://cert.be/en/report-incident",
        "email": "cert@cert.be",
        "country": "Belgio",
    },
    "NL": {
        "name": "NCSC-NL",
        "portal": "https://www.ncsc.nl/contact",
        "email": "ncsc@ncsc.nl",
        "country": "Paesi Bassi",
    },
    "ES": {
        "name": "CCN-CERT / INCIBE",
        "portal": "https://www.incibe.es/incibe-cert/alerta-temprana",
        "email": "incidencias@incibe.es",
        "country": "Spagna",
    },
    "AT": {
        "name": "CERT.at / GovCERT Austria",
        "portal": "https://www.cert.at/en/reporting/",
        "email": "reports@cert.at",
        "country": "Austria",
    },
    "SE": {
        "name": "NCSC-SE / CERT-SE",
        "portal": "https://www.cert.se/anmal-incident",
        "email": "cert@cert.se",
        "country": "Svezia",
    },
    "CZ": {
        "name": "NUKIB — Narodni urad pro kybernetickou a informacni bezpecnost",
        "portal": "https://www.nukib.cz/cs/infoservis/",
        "email": "incident@nukib.cz",
        "country": "Repubblica Ceca",
    },
}


class BusinessUnit(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    manager = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )


class Plant(BaseModel):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    country = models.CharField(
        max_length=10,
        choices=EU_COUNTRIES,
        default="IT",
        help_text="Paese del sito — determina il CSIRT NIS2 competente",
    )
    bu = models.ForeignKey(
        BusinessUnit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="plants",
    )
    parent_plant = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sub_plants",
    )
    has_ot = models.BooleanField(default=False)
    purdue_level_max = models.IntegerField(null=True, blank=True)
    nis2_scope = models.CharField(
        max_length=20,
        choices=[
            ("essenziale", "Essenziale"),
            ("importante", "Importante"),
            ("non_soggetto", "Non soggetto"),
        ],
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("attivo", "Attivo"),
            ("in_dismissione", "In dismissione"),
            ("chiuso", "Chiuso"),
        ],
        default="attivo",
    )
    address = models.TextField(blank=True)
    timezone = models.CharField(max_length=50, default="Europe/Rome")
    logo_url = models.CharField(
        max_length=500,
        blank=True,
        help_text="URL del logo per questo sito (usato in report/export). Può essere assoluto o relativo (es. /media/...).",
    )
    nis2_sector = models.CharField(
        max_length=100,
        blank=True,
        help_text="Settore NIS2 (es. Manifattura - Automotive) — usato in notifiche CSIRT",
    )
    nis2_subsector = models.CharField(
        max_length=100,
        blank=True,
        help_text="Sottosettore NIS2 — usato in notifiche CSIRT",
    )
    legal_entity_name = models.CharField(
        max_length=300,
        blank=True,
        help_text="Ragione sociale per notifiche formali NIS2",
    )
    legal_entity_vat = models.CharField(
        max_length=50,
        blank=True,
        help_text="Partita IVA / VAT per notifiche formali NIS2",
    )
    nis2_activity_description = models.TextField(
        blank=True,
        help_text="Descrizione attività NIS2 del sito per documenti formali",
    )
    domain = models.CharField(
        max_length=255,
        blank=True,
        help_text="Dominio internet principale del sito (es. azienda.it) — usato dal modulo OSINT per monitoraggio passivo.",
    )
    additional_domains = models.JSONField(
        default=list,
        blank=True,
        help_text="Domini aggiuntivi associati al sito (es. plant-milano.azienda.it). Array di stringhe. Letti dal modulo OSINT.",
    )

    class Meta:
        ordering = ["code"]

    def clean(self):
        if self.parent_plant and self.parent_plant.parent_plant:
            raise ValidationError(_("Max 1 livello di nesting per i sub-plant."))

    @property
    def is_nis2_subject(self):
        return self.nis2_scope in ("essenziale", "importante")


class PlantFramework(BaseModel):
    plant = models.ForeignKey(Plant, on_delete=models.CASCADE, related_name="frameworks")
    framework = models.ForeignKey("controls.Framework", on_delete=models.CASCADE)
    active_from = models.DateField()
    level = models.CharField(max_length=10, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["plant", "framework"]

