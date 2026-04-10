"""
Management command: import_risk_register
Importa il registro rischi Excel (26 scenari) nel database GRC.

Uso:
    python manage.py import_risk_register [--dry-run] [--plant-name "Chivasso Via Meliga Plant"] [--owner-email "federico.pino@it.sumiriko.com"]
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.plants.models import Plant
from apps.risk.models import RiskAssessment, RiskMitigationPlan, THREAT_CATEGORIES

logger = logging.getLogger(__name__)
User = get_user_model()

# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------
PROB_MAP = {
    "very low": 1, "very_low": 1,
    "low": 2,
    "medium": 3, "moderate": 3,
    "high": 4,
    "very high": 5, "very_high": 5,
}
IMPACT_MAP = {
    "negligible": 1,
    "minor": 2,
    "moderate": 3,
    "significant": 4, "major": 4,
    "severe": 5, "critical": 5,
}
TREATMENT_MAP = {
    "mitigate": "mitigare",
    "accept": "accettare",
    "transfer": "trasferire",
    "avoid": "evitare",
}
NIS2_RELEVANCE_MAP = {
    "yes – non significant": "non_significativo",
    "yes – potentially significant": "potenzialmente_significativo",
    "yes – significant": "significativo",
    "no": "",
    "": "",
}
NIS2_ART21_MAP = {
    "art.21(2)(a)": "art21_a",
    "art.21(2)(b)": "art21_b",
    "art.21(2)(c)": "art21_c",
    "art.21(2)(d)": "art21_d",
    "art.21(2)(e)": "art21_e",
    "art.21(2)(f)": "art21_f",
    "art.21(2)(g)": "art21_g",
    "art.21(2)(h)": "art21_h",
    "art.21(2)(i)": "art21_i",
    "art.21(2)(j)": "art21_j",
}
STATUS_MAP = {
    "complete": "completato",
    "completed": "completato",
    "draft": "bozza",
    "in progress": "bozza",
    "": "bozza",
}
VALID_THREAT_KEYS = {k for k, _ in THREAT_CATEGORIES}


def _map_prob(val: str) -> int | None:
    return PROB_MAP.get(val.strip().lower())


def _map_impact(val: str) -> int | None:
    return IMPACT_MAP.get(val.strip().lower())


def _map_treatment(val: str) -> str:
    return TREATMENT_MAP.get(val.strip().lower(), "mitigare")


def _map_nis2_relevance(val: str) -> str:
    return NIS2_RELEVANCE_MAP.get(val.strip().lower(), "")


def _map_nis2_art21(val: str) -> str:
    if not val:
        return ""
    # e.g. "Art.21(2)(g) – Igiene informatica e formazione" → "art21_g"
    key = val.strip().split("–")[0].strip().lower()  # "art.21(2)(g)"
    return NIS2_ART21_MAP.get(key, "")


def _map_threat(val: str) -> str:
    key = val.strip().lower().replace(" ", "_").replace("/", "_")
    if key in VALID_THREAT_KEYS:
        return key
    # Loose fallback mapping
    fallbacks = {
        "accesso_non_autorizzato": "accesso_non_autorizzato",
        "unauthorized_access": "accesso_non_autorizzato",
        "malware": "malware_ransomware",
        "ransomware": "malware_ransomware",
        "data_breach": "data_breach",
        "data_leakage": "data_breach",
        "phishing": "phishing_social",
        "social_engineering": "phishing_social",
        "hardware_failure": "guasto_hw_sw",
        "software_failure": "guasto_hw_sw",
        "guasto": "guasto_hw_sw",
        "natural_disaster": "disastro_naturale",
        "human_error": "errore_umano",
        "errore": "errore_umano",
        "supply_chain": "attacco_supply_chain",
        "ddos": "ddos",
        "dos": "ddos",
        "insider": "insider_threat",
        "theft": "furto_perdita",
        "furto": "furto_perdita",
    }
    for pattern, mapped in fallbacks.items():
        if pattern in key:
            return mapped
    return "altro"


# ---------------------------------------------------------------------------
# Risk data — 26 scenari da registro Excel SumiRiko
# ---------------------------------------------------------------------------
RISKS = [
    {
        "name": "Accesso non autorizzato ai sistemi IT",
        "threat_category": "accesso_non_autorizzato",
        "cause": "Credenziali deboli o rubate, assenza di MFA, policy di accesso inadeguate",
        "consequence": "Compromissione di dati sensibili, interruzione dei sistemi, violazione di conformità",
        "inherent_probability": 4,
        "inherent_impact": 4,
        "probability": 2,
        "impact": 4,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_i",
        "nis2_relevance": "significativo",
        "impacted_systems": "Active Directory, VPN, ERP SAP",
        "status": "completato",
        "action": "Implementare MFA su tutti i sistemi critici; rafforzare password policy; revisione trimestrale degli accessi privilegiati",
    },
    {
        "name": "Attacco ransomware / malware",
        "threat_category": "malware_ransomware",
        "cause": "Phishing, vulnerabilità software non patchate, navigazione su siti non sicuri",
        "consequence": "Cifratura e perdita di dati, fermo produzione, costi di ripristino elevati",
        "inherent_probability": 3,
        "inherent_impact": 5,
        "probability": 2,
        "impact": 5,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_b",
        "nis2_relevance": "significativo",
        "impacted_systems": "Server produzione, NAS backup, postazioni utente",
        "status": "completato",
        "action": "Deploy EDR su tutti gli endpoint; segmentazione VLAN; backup offsite giornaliero testato trimestralmente; piano IR documentato",
    },
    {
        "name": "Data breach / fuga di dati",
        "threat_category": "data_breach",
        "cause": "Accesso non autorizzato, misconfiguration cloud, insider malintenzionato",
        "consequence": "Sanzioni GDPR, danno reputazionale, perdita di fiducia dei clienti OEM",
        "inherent_probability": 3,
        "inherent_impact": 4,
        "probability": 2,
        "impact": 4,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_h",
        "nis2_relevance": "significativo",
        "impacted_systems": "Database clienti, repository documenti, email",
        "status": "completato",
        "action": "DLP su email e endpoint; cifratura dati at-rest e in-transit; audit accessi mensile; training GDPR annuale",
    },
    {
        "name": "Phishing / Social engineering",
        "threat_category": "phishing_social",
        "cause": "Email di phishing mirate, mancanza di consapevolezza degli utenti",
        "consequence": "Furto credenziali, compromissione account email, accesso a sistemi interni",
        "inherent_probability": 4,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_g",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Email Office 365, Active Directory",
        "status": "completato",
        "action": "Campagne di phishing simulato (KnowBe4) trimestrali; formazione awareness annuale; filtri anti-phishing e DMARC configurati",
    },
    {
        "name": "Guasto infrastruttura IT critica",
        "threat_category": "guasto_hw_sw",
        "cause": "Obsolescenza hardware, mancanza di ridondanza, errori di configurazione",
        "consequence": "Interruzione produzione, perdita di dati, SLA non rispettati verso OEM",
        "inherent_probability": 3,
        "inherent_impact": 4,
        "probability": 2,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_c",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Server ESXi, storage SAN, switch core",
        "status": "completato",
        "action": "Piano di refresh hardware; implementazione cluster HA VMware; test di failover semestrale; monitoraggio proattivo (Zabbix)",
    },
    {
        "name": "Interruzione servizi cloud / SaaS",
        "threat_category": "guasto_hw_sw",
        "cause": "Downtime provider cloud, problemi di connettività, mancanza di SLA adeguati",
        "consequence": "Blocco operatività su strumenti collaborativi e gestionali cloud-based",
        "inherent_probability": 3,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_c",
        "nis2_relevance": "non_significativo",
        "impacted_systems": "Office 365, Teams, SharePoint, SAP Business ByDesign",
        "status": "completato",
        "action": "Contratti SaaS con SLA ≥ 99.9%; procedure di fallback offline documentate; monitoraggio disponibilità servizi",
    },
    {
        "name": "Vulnerabilità software non patchate",
        "threat_category": "guasto_hw_sw",
        "cause": "Ciclo di patching lento, dipendenze legacy, mancanza di processo formalizzato",
        "consequence": "Exploitation di CVE note, compromissione sistemi, lateral movement attaccanti",
        "inherent_probability": 4,
        "inherent_impact": 4,
        "probability": 2,
        "impact": 4,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_e",
        "nis2_relevance": "significativo",
        "impacted_systems": "Tutti i sistemi Windows/Linux, applicazioni web interne",
        "status": "completato",
        "action": "Vulnerability management mensile (Tenable); patching critico entro 72h; inventario asset aggiornato",
    },
    {
        "name": "Attacco alla supply chain IT",
        "threat_category": "attacco_supply_chain",
        "cause": "Fornitori IT con accesso remoto non sicuro, software compromessi, aggiornamenti malevoli",
        "consequence": "Compromissione sistemi interni tramite vettore fornitore fidato",
        "inherent_probability": 2,
        "inherent_impact": 5,
        "probability": 1,
        "impact": 5,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_d",
        "nis2_relevance": "significativo",
        "impacted_systems": "Reti OT/IT, sistemi di controllo industriale, ERP",
        "status": "completato",
        "action": "Vendor security assessment annuale; accesso remoto fornitori solo via VPN con MFA e sessioni registrate; contratti con clausole sicurezza NIS2",
    },
    {
        "name": "Insider threat (dipendente malintenzionato)",
        "threat_category": "insider_threat",
        "cause": "Dipendente insoddisfatto o corrotto con accesso privilegiato",
        "consequence": "Esfiltrazione dati confidenziali, sabotaggio sistemi, furto proprietà intellettuale",
        "inherent_probability": 2,
        "inherent_impact": 4,
        "probability": 1,
        "impact": 4,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_i",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "ERP, sistemi di progettazione CAD, repository codice",
        "status": "completato",
        "action": "Principio del minimo privilegio; log e alert su accessi anomali (SIEM); processo di offboarding con revoca immediata accessi; DLP",
    },
    {
        "name": "Furto o perdita dispositivi mobili/laptop",
        "threat_category": "furto_perdita",
        "cause": "Furto fisico di laptop/tablet, smarrimento in trasferta",
        "consequence": "Accesso non autorizzato a dati aziendali, violazione GDPR se dati personali esposti",
        "inherent_probability": 3,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 2,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_h",
        "nis2_relevance": "non_significativo",
        "impacted_systems": "Laptop aziendali, tablet, smartphone",
        "status": "completato",
        "action": "Full-disk encryption (BitLocker); MDM con remote wipe; policy utilizzo dispositivi in trasferta; inventario dispositivi",
    },
    {
        "name": "Attacco DoS / DDoS",
        "threat_category": "ddos",
        "cause": "Attacco volumetrico esterno verso infrastruttura esposta su internet",
        "consequence": "Interruzione servizi web e portali clienti/fornitori, danno reputazionale",
        "inherent_probability": 2,
        "inherent_impact": 3,
        "probability": 1,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_b",
        "nis2_relevance": "non_significativo",
        "impacted_systems": "Portale fornitori, sito web, servizi esposti internet",
        "status": "completato",
        "action": "Servizio anti-DDoS (Cloudflare); rate limiting su API pubbliche; piano di risposta DDoS documentato",
    },
    {
        "name": "Errore umano nella gestione dei sistemi IT",
        "threat_category": "errore_umano",
        "cause": "Configurazioni errate, cancellazione accidentale di dati, operazioni non autorizzate",
        "consequence": "Perdita di dati, interruzione servizi, ripristino da backup con downtime",
        "inherent_probability": 4,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_g",
        "nis2_relevance": "non_significativo",
        "impacted_systems": "Tutti i sistemi IT, database, ambienti di produzione",
        "status": "completato",
        "action": "Procedure operative documentate (SOP); change management formalizzato; test in ambienti di staging; backup giornaliero verificato",
    },
    {
        "name": "Mancanza di continuità operativa IT (BCP/DR)",
        "threat_category": "disastro_naturale",
        "cause": "Assenza di piano BCP/DR aggiornato e testato, dipendenza da singolo datacenter",
        "consequence": "RTO/RPO non rispettati in caso di incidente grave, perdita di dati critica",
        "inherent_probability": 2,
        "inherent_impact": 5,
        "probability": 1,
        "impact": 4,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_c",
        "nis2_relevance": "significativo",
        "impacted_systems": "Datacenter primario, sistemi ERP, sistemi produzione",
        "status": "completato",
        "action": "Piano BCP/DR documentato e approvato; DR site configurato; test di ripristino annuale; RTO target 4h per sistemi critici",
    },
    {
        "name": "Non conformità GDPR nella gestione dei dati",
        "threat_category": "data_breach",
        "cause": "Processi di gestione dati non conformi, retention non rispettata, consensi mancanti",
        "consequence": "Sanzioni GDPR fino al 4% fatturato globale, danno reputazionale",
        "inherent_probability": 2,
        "inherent_impact": 4,
        "probability": 1,
        "impact": 4,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_h",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Database HR, CRM, sistemi di gestione candidature",
        "status": "completato",
        "action": "Registro trattamenti aggiornato; DPIA per trattamenti ad alto rischio; policy retention dati implementata; DPO nominato",
    },
    {
        "name": "Accesso fisico non autorizzato al datacenter/server room",
        "threat_category": "accesso_non_autorizzato",
        "cause": "Controlli di accesso fisico inadeguati, visitatori non scortati, badge sharing",
        "consequence": "Manipolazione hardware, furto server/storage, installazione di dispositivi spia",
        "inherent_probability": 2,
        "inherent_impact": 4,
        "probability": 1,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_i",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Server room Chivasso, armadi rack, UPS",
        "status": "completato",
        "action": "Controllo accessi biometrico/badge; registro accessi; CCTV operativa 24/7; policy visitatori con scorta obbligatoria",
    },
    {
        "name": "Obsolescenza tecnologica sistemi OT/SCADA",
        "threat_category": "guasto_hw_sw",
        "cause": "Sistemi di controllo industriale end-of-life, OS non supportati, aggiornamenti impossibili",
        "consequence": "Vulnerabilità non patchabili, fermo impianto per guasto, sicurezza OT compromessa",
        "inherent_probability": 3,
        "inherent_impact": 4,
        "probability": 2,
        "impact": 4,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_e",
        "nis2_relevance": "significativo",
        "impacted_systems": "PLC linee produzione, SCADA, HMI industriali",
        "status": "completato",
        "action": "Inventario sistemi OT con EOL tracking; segmentazione rete IT/OT; piano di sostituzione HW con budget approvato; compensating controls",
    },
    {
        "name": "Rischio di terze parti / gestione vendor",
        "threat_category": "attacco_supply_chain",
        "cause": "Fornitori con postura di sicurezza inadeguata, assenza di audit, contratti senza clausole sicurezza",
        "consequence": "Compromissione dati tramite fornitore, violazione SLA, responsabilità contrattuale",
        "inherent_probability": 3,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_d",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Sistemi condivisi con fornitori, API di integrazione, VPN fornitori",
        "status": "completato",
        "action": "Vendor risk assessment annuale con questionario di sicurezza; clausole sicurezza nei contratti; registro fornitori critici aggiornato",
    },
    {
        "name": "Insufficiente gestione delle identità e degli accessi (IAM)",
        "threat_category": "accesso_non_autorizzato",
        "cause": "Processi di provisioning/deprovisioning manuali, account orfani, privilegi eccessivi",
        "consequence": "Accessi non autorizzati, violazione principio minimo privilegio, rischio insider",
        "inherent_probability": 3,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_i",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Active Directory, sistemi applicativi, ERP SAP",
        "status": "completato",
        "action": "Implementazione processo IAM automatizzato; revisione accessi semestrale; deprovisioning immediato al termine rapporto; PAM per admin",
    },
    {
        "name": "Mancanza di cifratura dati sensibili",
        "threat_category": "data_breach",
        "cause": "Dati sensibili memorizzati o trasmessi in chiaro, mancanza di policy cifratura",
        "consequence": "Esposizione dati in caso di accesso non autorizzato o intercettazione traffico",
        "inherent_probability": 3,
        "inherent_impact": 4,
        "probability": 1,
        "impact": 4,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_h",
        "nis2_relevance": "significativo",
        "impacted_systems": "Database, share di rete, email, laptop",
        "status": "completato",
        "action": "Cifratura full-disk su tutti i laptop (BitLocker); TLS 1.2+ su tutte le comunicazioni; cifratura DB per dati classificati; policy crittografia aziendale",
    },
    {
        "name": "Inadeguata gestione degli incidenti di sicurezza",
        "threat_category": "altro",
        "cause": "Assenza di IRP formale, SIEM non configurato, tempi di rilevamento eccessivi",
        "consequence": "Incidenti non gestiti correttamente, escalation NIS2 mancata, danni amplificati",
        "inherent_probability": 3,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_b",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Tutti i sistemi IT/OT",
        "status": "completato",
        "action": "IRP (Incident Response Plan) documentato e approvato; SIEM configurato con alert; test annuale incident response (tabletop); designazione CSIRT interno",
    },
    {
        "name": "Mancata formazione e awareness del personale",
        "threat_category": "errore_umano",
        "cause": "Programma di formazione sicurezza assente o non aggiornato, bassa partecipazione",
        "consequence": "Maggiore suscettibilità a phishing, errori operativi, violazioni policy",
        "inherent_probability": 4,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 2,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_g",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Tutti gli utenti aziendali",
        "status": "completato",
        "action": "Piano formazione annuale obbligatorio (security awareness + GDPR); phishing simulation trimestrale; tracking completion rate ≥ 95%",
    },
    {
        "name": "Utilizzo di dispositivi personali (BYOD) non gestiti",
        "threat_category": "accesso_non_autorizzato",
        "cause": "Accesso a risorse aziendali da dispositivi personali non sicuri, assenza policy BYOD",
        "consequence": "Esfiltrazione dati, introduzione malware, perdita controllo endpoint",
        "inherent_probability": 3,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 2,
        "treatment": "accettare",
        "nis2_art21_category": "art21_i",
        "nis2_relevance": "non_significativo",
        "impacted_systems": "Reti WiFi aziendali, portali web, email",
        "status": "completato",
        "action": "Policy BYOD approvata; rete Guest WiFi separata per dispositivi personali; NAC per controllo accesso rete; accettazione residuo con policy",
    },
    {
        "name": "Interruzione alimentazione elettrica",
        "threat_category": "disastro_naturale",
        "cause": "Black-out rete elettrica, guasto UPS, mancanza di gruppo elettrogeno",
        "consequence": "Fermo immediato sistemi IT e produzione, rischio perdita dati su transazioni in corso",
        "inherent_probability": 2,
        "inherent_impact": 3,
        "probability": 1,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_c",
        "nis2_relevance": "non_significativo",
        "impacted_systems": "Datacenter, linee produzione, impianti OT",
        "status": "completato",
        "action": "UPS dimensionati per autonomia ≥ 30 min sui sistemi critici; generatore diesel testato mensilmente; procedura shutdown ordinato documentata",
    },
    {
        "name": "Mancata verifica dell'efficacia dei controlli di sicurezza",
        "threat_category": "altro",
        "cause": "Assenza di audit interni, penetration test non eseguiti, KPI sicurezza non monitorati",
        "consequence": "Controlli inefficaci non rilevati, falsa sensazione di sicurezza, audit TISAX/NIS2 negativo",
        "inherent_probability": 3,
        "inherent_impact": 3,
        "probability": 2,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_f",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Intera infrastruttura IT/OT",
        "status": "completato",
        "action": "Penetration test annuale esterno; audit interni trimestrali; dashboard KPI sicurezza condivisa con management; review post-assessment TISAX",
    },
    {
        "name": "Rischio di non conformità TISAX L2",
        "threat_category": "altro",
        "cause": "Requisiti TISAX non completamente implementati, evidenze mancanti, processi non maturi",
        "consequence": "Perdita certificazione TISAX, impossibilità di lavorare con OEM automotive, danno commerciale",
        "inherent_probability": 2,
        "inherent_impact": 5,
        "probability": 1,
        "impact": 4,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_a",
        "nis2_relevance": "significativo",
        "impacted_systems": "Tutti i sistemi che trattano dati protetti OEM",
        "status": "completato",
        "action": "Gap analysis TISAX annuale; remediation plan con owner e scadenze; raccolta evidenze continua sulla piattaforma GRC; assessment esterno programmato",
    },
    {
        "name": "Comunicazioni non sicure con partner / OEM",
        "threat_category": "data_breach",
        "cause": "Utilizzo di canali email non cifrati, assenza di portali sicuri per scambio documenti",
        "consequence": "Intercettazione di dati tecnici riservati (disegni, specifiche), violazione accordi NDA",
        "inherent_probability": 2,
        "inherent_impact": 4,
        "probability": 1,
        "impact": 3,
        "treatment": "mitigare",
        "nis2_art21_category": "art21_j",
        "nis2_relevance": "potenzialmente_significativo",
        "impacted_systems": "Email, portale fornitori, sistemi di scambio file",
        "status": "completato",
        "action": "Utilizzo portali sicuri OEM per documenti riservati; cifratura email S/MIME per comunicazioni sensibili; classificazione documenti e policy distribuzione",
    },
]


class Command(BaseCommand):
    help = "Importa il registro rischi (26 scenari) nel database GRC"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa verrebbe importato senza scrivere nel DB",
        )
        parser.add_argument(
            "--plant-name",
            default="Chivasso Via Meliga Plant",
            help="Nome del plant di destinazione",
        )
        parser.add_argument(
            "--owner-email",
            default="federico.pino@it.sumiriko.com",
            help="Email del risk owner",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        plant_name = options["plant_name"]
        owner_email = options["owner_email"]

        # Resolve plant
        try:
            plant = Plant.objects.get(name=plant_name, deleted_at__isnull=True)
        except Plant.DoesNotExist:
            raise CommandError(f"Plant '{plant_name}' non trovato nel database.")

        # Resolve owner
        try:
            owner = User.objects.get(email=owner_email, is_active=True)
        except User.DoesNotExist:
            raise CommandError(f"Utente '{owner_email}' non trovato nel database.")

        self.stdout.write(f"Plant: {plant.name} ({plant.id})")
        self.stdout.write(f"Owner: {owner.get_full_name()} <{owner.email}> (id={owner.id})")
        self.stdout.write(f"Dry-run: {dry_run}")
        self.stdout.write("=" * 60)

        created = 0
        skipped = 0

        for risk_data in RISKS:
            name = risk_data["name"]

            # Idempotency: skip if already exists with same name + plant
            exists = RiskAssessment.objects.filter(
                name=name, plant=plant, deleted_at__isnull=True
            ).exists()
            if exists:
                self.stdout.write(self.style.WARNING(f"  SKIP (già presente): {name}"))
                skipped += 1
                continue

            score = risk_data["probability"] * risk_data["impact"]
            inherent_score = risk_data["inherent_probability"] * risk_data["inherent_impact"]

            if dry_run:
                self.stdout.write(
                    f"  [DRY-RUN] Crea: {name} | score={score} | {risk_data['status']} | "
                    f"NIS2={risk_data['nis2_relevance']}"
                )
                created += 1
                continue

            assessment = RiskAssessment.objects.create(
                plant=plant,
                name=name,
                threat_category=risk_data["threat_category"],
                cause=risk_data.get("cause", ""),
                consequence=risk_data.get("consequence", ""),
                assessment_type="IT",
                inherent_probability=risk_data["inherent_probability"],
                inherent_impact=risk_data["inherent_impact"],
                inherent_score=inherent_score,
                probability=risk_data["probability"],
                impact=risk_data["impact"],
                score=score,
                treatment=risk_data["treatment"],
                status=risk_data["status"],
                nis2_art21_category=risk_data.get("nis2_art21_category", ""),
                nis2_relevance=risk_data.get("nis2_relevance", ""),
                impacted_systems=risk_data.get("impacted_systems", ""),
                owner=owner,
                assessed_by=owner,
                assessed_at=timezone.now(),
                created_by=owner,
            )

            # Create mitigation plan if action text is present
            action_text = risk_data.get("action", "")
            if action_text:
                from datetime import date, timedelta
                RiskMitigationPlan.objects.create(
                    assessment=assessment,
                    action=action_text,
                    owner=owner,
                    due_date=date.today() + timedelta(days=180),
                    created_by=owner,
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  CREA: {name} | score={score} | {risk_data['status']}"
                )
            )
            created += 1

        self.stdout.write("=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY-RUN: {created} da creare, {skipped} già presenti"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Completato: {created} creati, {skipped} saltati"))
