# Conformità & Privacy — govrico

> Sintesi pubblica delle misure di **privacy e sicurezza by-design** integrate in govrico.
> Il fascicolo di conformità completo (DPIA, ROPA, DPA, informativa, checklist per scenario)
> è mantenuto come deliverable ed è **disponibile per i clienti / su richiesta**.

govrico è una piattaforma GRC (governance, rischio, conformità) progettata per supportare
TISAX, NIS2 e ISO 27001, ed è essa stessa costruita per rispettare il quadro normativo UE
applicabile: **GDPR** (+ DPIA), **AI Act**, **Data Act**, **Cyber Resilience Act**, **NIS2**.

## Misure integrate nel prodotto (privacy/security-by-design)

- **Audit trail append-only** con catena di hash verificabile (accountability, anti-tamper).
- **Pseudonimizzazione** dell'autore nei log; nessun identificatore diretto nei payload di audit.
- **RBAC a privilegio minimo** con scoping per sito; esclusione dei ruoli esterni dai dati di esposizione.
- **Cifratura AES-256 (FERNET)** dei segreti; MFA; password policy; JWT con rotazione/blacklist; rate-limiting.
- **AI con minimizzazione**: sanitizzazione degli input, **opzione di elaborazione locale** (nessun
  trasferimento extra-UE), **marcatura esplicita dei contenuti generati da AI**, supervisione umana,
  retention dei log di interazione.
- **Telemetria privacy-first**: Session Replay **disattivato di default**, configurabile.
- **Portabilità dei dati** (export in formato aperto) e **cancellazione** (anonimizzazione + purge
  dei record oltre la retention).
- **Gestione vulnerabilità** in CI (`pip-audit` / `npm audit`) e **SBOM** (CycloneDX) per release.

## Documenti pubblici correlati
- [`SECURITY.md`](SECURITY.md) — vulnerability disclosure coordinata (allineata al CRA).

## Responsabilità (modello multi-scenario)
A seconda di come govrico viene distribuito (self-hosted dal cliente, SaaS, o gestito), gli
obblighi normativi si ripartiscono tra fornitore, titolare e operatore. Il fascicolo completo
include le **checklist per ciascuno scenario** ed è fornito ai clienti.

> Nota: questo documento è informativo e non costituisce parere legale.
