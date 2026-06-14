# Retention & cancellazione (GDPR Art. 5.1.e, 17)

> ⚠️ Bozza tecnica, non parere legale. I periodi marcati `[DA COMPILARE]` sono scelte del
> **titolare** (vincoli settoriali/contrattuali). Questo doc fotografa la retention *tecnica*
> attuale e i meccanismi di cancellazione, e segnala le decisioni da formalizzare.

## 1. Principio
- **Limitazione della conservazione**: i dati sono conservati per il tempo necessario alle
  finalità (sicurezza, conformità) e poi minimizzati/eliminati.
- **Eccezione audit**: l'`AuditLog` è **append-only/immutabile** e conservato in modo
  permanente per obbligo legale/legittimo interesse (accountability di sicurezza); è
  pseudonimizzato a monte. Vedi [`audit-log-pii-assessment.md`](audit-log-pii-assessment.md).

## 2. Retention per categoria (stato tecnico attuale)

| Categoria | Dove | Retention attuale | Meccanismo | Note / base |
|-----------|------|-------------------|------------|-------------|
| **Audit log** | `audit_log` | **Permanente** (immutabile) | nessuna cancellazione (trigger anti-tamper) | Obbligo legale/legittimo interesse; pseudonimizzato |
| Backup DB | `BACKUP_DIR` | **30 giorni** | `BACKUP_RETENTION_DAYS=30`, task notturno | Include i RESTORED |
| Risultati task Celery | `django_celery_results` | **7 giorni** | `cleanup_celery_results` | Tecnico, no PII rilevante |
| Scan OSINT | `osint` | **Tiered** (recenti + mensili) | `cleanup_old_scans` | Bilanciato audit/DB |
| Token auditor esterni | `auth_grc` | Scadenza per `valid_days` | expiry su token | Accesso temporaneo |
| **Log interazioni AI** | `ai_interaction_log` | **⚠️ indefinita (nessun cleanup)** | — | **Gap**: output AI (possibile PII incidentale) senza retention → vedi §5 |
| Record soft-deleted | tabelle BaseModel | Conservati (`deleted_at`) | non purgati | Recuperabili; definire purge dopo X `[DA COMPILARE]` |
| **Phishing/training per dipendente** | `training` | `[DA COMPILARE]` | — | DPIA: minimizzare; valutare aggregazione dopo X |
| Incidenti / documenti / evidenze | vari | `[DA COMPILARE]` (spesso pluriennale per compliance) | soft delete | Vincoli ISO/NIS2/contrattuali |
| Account utenti | `auth.User` + `UserPlantAccess` | finché attivo + `[DA COMPILARE]` post-cessazione | disattivazione + `anonymize_user()` | — |

## 3. Diritto alla cancellazione (Art. 17)
- **Meccanismo**: `auth_grc.services.anonymize_user()` (GDPR Art. 17): rende anonimi i campi
  identificativi dell'utente (nome, email, ecc.) mantenendo l'integrità referenziale.
- **Soft delete**: i record di dominio usano `soft_delete()` (recuperabili); definire un
  **purge definitivo** dopo il periodo di retention scelto.
- **Portabilità (Art. 20)**: export CSV/backup disponibili (vedi Data Act).

## 4. Riconciliazione cancellazione ↔ audit immutabile
La tensione tra Art. 17 (cancellazione) e audit immutabile è gestita così:
1. `anonymize_user()` recide il legame **identità ↔ persona** sul record `User`.
2. Le voci di audit restano ma contengono solo: `user_id` (UUID, ora privo di referente
   identificabile dopo l'anonimizzazione) + email **pseudonimizzata** + azioni. Nessun
   identificatore diretto (verificato).
3. Risultato: la persona non è più identificabile *tramite* l'audit dopo l'anonimizzazione,
   mentre l'evidenza di sicurezza (chi-fece-cosa, in forma pseudonima) è preservata per
   l'obbligo legale. → bilanciamento conforme se **documentato** (questo doc + informativa).

⚠️ Da verificare nel completamento: che `anonymize_user()` copra **tutti** i punti dove il
nome/email dell'utente potrebbe comparire in chiaro (es. campi `*_by_name` calcolati a
runtime non persistono; i FK usano UUID → ok).

## 5. Azioni residue
1. **`[DA COMPILARE]`**: periodi di conservazione per categoria (titolare + vincoli settoriali).
2. **Gap tecnico**: aggiungere una **retention per `AiInteractionLog`** (es. cleanup oltre N
   mesi) — oggi cresce indefinitamente e può contenere PII incidentale negli output.
3. Definire **purge definitivo** dei record soft-deleted dopo il periodo di retention.
4. Per phishing/training: valutare **aggregazione/anonimizzazione** dopo il periodo utile (DPIA §6).
5. Formalizzare il tutto in informativa (Art. 13-14) e ROPA (Art. 30).
