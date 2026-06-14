# Compliance Register (master)

> ⚠️ Bozza tecnica, non parere legale. Vedi [README](README.md) per il modello e la legenda.

**Owner**: P = Prodotto (software) · D = Deployer/Titolare (cliente) · O = Operatore (tu, SaaS/managed).
**Stato**: ✅ in essere · 🟡 parziale · ⬜ da fare · 📄 serve documento.

## GDPR (Reg. 2016/679)

| Art. | Obbligo | Owner | Stato | Evidenza / azione |
|------|---------|-------|-------|-------------------|
| 5, 25 | Minimizzazione, privacy-by-design/default | P | ✅ | Email pseudonimizzata audit; no PII nei log (regola #11); Sanitizer; RBAC scoping |
| 5.1.e | Limitazione conservazione (retention) | P+D/O | 🟡📄 | Backup 30gg, Celery 7gg, OSINT tiered, **AI log 365gg**, audit permanente (giustificato) → [`gdpr/retention-and-erasure.md`](gdpr/retention-and-erasure.md); restano periodi `[DA COMPILARE]` del titolare |
| 6/9 | Base giuridica (incl. monitoraggio lavoratori phishing/training) | D/O | ⬜📄 | Da definire per trattamento; possibile consultazione RSU/comitato (DE/IT) |
| 13-14 | Informativa agli interessati | D/O | ⬜📄 | Template informativa per utenti/dipendenti |
| 15-22 | Diritti interessati (accesso, rettifica, **cancellazione**, portabilità) | P+D/O | 🟡 | `anonymize_user()` (Art.17); export CSV/backup (Art.20); doc bilanciamento vs audit immutabile |
| 17 vs 5.1.e | Cancellazione vs **audit append-only** | P | 🟡📄 | Audit immutabile per obbligo legale/legittimo interesse; email già pseudonimizzata → documentare in retention policy. **Payload verificati**: nessun identificatore diretto, prosa libera troncata → [`gdpr/audit-log-pii-assessment.md`](gdpr/audit-log-pii-assessment.md) |
| 28 | Contratto responsabile (DPA) | O | ⬜📄 | Necessario in SaaS/managed; e verso i **sub-processor AI** (Anthropic/OpenAI) |
| 30 | Registro dei trattamenti (ROPA) | D/O | ⬜📄 | `gdpr/ropa.md` |
| 32 | Sicurezza del trattamento | P | ✅ | FERNET AES-256, RBAC, MFA, password policy, MIME-check, JWT blacklist, rate-limit, audit hash-chain |
| 33-34 | Notifica data breach | D/O | 🟡 | Modulo incidenti M09 (NIS2) riusabile; definire processo/tempistiche GDPR |
| 35 | **DPIA** | D/O | 🟡📄 | Obbligatoria; **bozza pre-compilata** in [`gdpr/dpia.md`](gdpr/dpia.md) — restano i campi `[DA COMPILARE]` del titolare |
| 44-49 | **Trasferimenti extra-UE** (provider AI USA) | P+D/O | 🟡📄 | **TIA** in [`gdpr/international-transfers.md`](gdpr/international-transfers.md): leva Ollama locale (zero-transfer) + sanitizzazione; restano scelta provider DPF/SCC + DPA `[titolare]` |

## AI Act (Reg. 2024/1689)

| Rif. | Obbligo | Owner | Stato | Evidenza / azione |
|------|---------|-------|-------|-------------------|
| Art. 6 / Annex III | Classificazione rischio (verificare Annex III.4 "gestione lavoratori") | P | 🟡📄 | Probabile **rischio limitato** (supporto + HIL, non valuta lavoratori); formalizzare in `ai/ai-system-inventory.md` |
| Art. 50 | **Trasparenza**: dichiarare interazione AI + marcare output generato | P | ✅ | Badge provider + **label "Contenuto generato da AI"** su banner/OSINT (anche nell'export) + disclaimer cockpit |
| Art. 14 | Supervisione umana | P | ✅ | Human-in-the-loop: output solo proposto, confirm/ignore (`AiInteractionLog`) |
| Art. 12 | Record-keeping | P | ✅ | `AiInteractionLog` (input_hash SHA-256, mai il testo; output, confirmer) |
| (GPAI) | Ruolo: **deployer** di GPAI di terzi | P | ✅ | Provider obligations su Anthropic/OpenAI; tu integratore/deployer |
| Art. 4 | AI literacy del personale | D/O | ⬜📄 | Nota istruzioni d'uso |

## Data Act (Reg. 2023/2854)

| Rif. | Obbligo | Owner | Stato | Evidenza / azione |
|------|---------|-------|-------|-------------------|
| Cap. III/IV | Condivisione dati / clausole eque (B2B) | O | ⬜📄 | Rilevante in SaaS; clausole contrattuali |
| Cap. VI | Switching / portabilità servizi cloud, no lock-in | P/O | 🟡 | Export CSV + backup esistono; verificare **export completo** del dato cliente |
| — | (Self-hosted: esposizione bassa) | D | ✅ | Il dato è già presso il cliente |

## Cyber Resilience Act (Reg. 2024/2847)

| Rif. | Obbligo | Owner | Stato | Evidenza / azione |
|------|---------|-------|-------|-------------------|
| — | Applicabilità | P | 🟡 | OSS **non commerciale esente**; con offerta commerciale/SaaS rientra |
| Annex I | Requisiti di sicurezza essenziali | P | ✅ | Vedi GDPR Art.32 (stesse misure) |
| Annex I.2 | **Gestione vulnerabilità** + SBOM | P | 🟡 | `pip-audit`/`npm audit` in CI; manca SBOM formale + processo patch documentato |
| Art. 13 | Vulnerability disclosure coordinata | P | ✅ | [`SECURITY.md`](../SECURITY.md) a root: reporting privato, SLA, safe harbor, SBOM, allineato CRA/ISO 29147 |
| — | Notifica incidenti/vuln sfruttate attivamente (~set 2026) | O | ⬜📄 | Processo se prodotto commerciale |

## NIS2 (Reg. 2022/2555)

| Rif. | Obbligo | Owner | Stato | Evidenza / azione |
|------|---------|-------|-------|-------------------|
| — | Clienti in scope (scopo del prodotto) | D | ✅ | È la funzione della piattaforma (M09, ecc.) |
| — | Tu in scope se "servizio digitale" (SaaS) | O | ⬜📄 | Valutare registrazione/obblighi come fornitore |
