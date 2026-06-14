# Valutazione PII nell'audit log

> ⚠️ Bozza tecnica, non parere legale. Alimenta `dpia.md` e `retention-and-erasure.md`.
> Data verifica: 2026-06-14 (analisi AST di tutte le chiamate `core.audit.log_action`).

## Contesto

L'`AuditLog` è **append-only / immutabile** (trigger PostgreSQL anti-tamper, hash-chain).
Qualsiasi dato personale finito in un payload vi **persiste in modo permanente**: la
minimizzazione a monte (cosa si scrive) è quindi più importante che altrove.
La regola interna #11 vieta di loggare dati personali diretti (email, CF, telefono).

## Metodo

Scansione AST di tutte le 227 chiamate `log_action(...)` in `apps/`, estrazione dei
`payload={...}` e classificazione delle chiavi a testo libero potenzialmente identificanti
(76 occorrenze in 29 file).

## Esito

### ✅ Identificatori diretti: NESSUNO nei payload (regola #11 rispettata)
Nessun payload logga **email, codice fiscale, numero di telefono, P.IVA** o indirizzi.
Dove serve riferire una persona si usa **sempre l'ID** (UUID), es.
`"terminated_user": str(assignment.user_id)`, `"old_user": str(...)`, mai il nome/email.
L'autore dell'azione è già pseudonimizzato a monte (`log_action` salva email
pseudonimizzata + `user_id`).

### 🟡 PII incidentale possibile in campi a testo libero
Tre categorie di valori a testo libero possono *incidentalmente* contenere il nome di una
persona digitato dall'utente:

| Categoria | Esempi di chiave | Rischio | Trattamento |
|-----------|------------------|---------|-------------|
| **Nomi di entità organizzative** | `name` (asset/plant/supplier/control/template) | Basso — sono nomi di cose/aziende, non persone (eccezione: ditta individuale) | **Mantenuti**: non sono dato personale; necessari alla leggibilità dell'audit |
| **Titoli di record** | `title` (incidente/task/documento/lesson/finding/…) | Medio — testo libero, può citare una persona | **Mantenuti** ma il dato è comunque sul record stesso (recuperabile via `entity_id`); accesso ristretto |
| **Note / motivazioni** | `note`, `notes`, `reason`, `motivo` | Più alto — prosa libera | **Troncati a 200 caratteri** (minimizzazione) + legittimo interesse |

## Misure applicate (2026-06-14)
- Troncamento a 200 char dei campi prosa liberi non ancora limitati: `documents` (notes
  approvazione/rifiuto), `controls.evaluated` (note), `management_review.approved` (note),
  `governance.role.terminated/replaced` (reason), `suppliers.nda.upload` (title).
- I campi già troncati ([:100]/[:200]) restano tali.

## Giustificazione del residuo (titoli/note nell'audit)

Il residuo di PII incidentale nei titoli/note è **trattamento lecito e proporzionato**:

- **Base giuridica**: legittimo interesse / obbligo legale — l'audit trail di sicurezza è
  un requisito di accountability (GDPR Art. 5.2, 30; ISO 27001 A.12.4; NIS2). La
  motivazione di un'azione (es. *perché* un ruolo è stato revocato o un documento respinto)
  è esattamente ciò che un audit trail deve registrare.
- **Minimizzazione**: identificatori diretti esclusi; prosa libera troncata; nomi solo
  quando organizzativi.
- **Limitazione d'accesso**: l'audit log è leggibile solo da super_admin / compliance /
  auditor interno-esterno (M10), non dai ruoli operativi.
- **Integrità**: l'immutabilità è essa stessa un controllo di sicurezza; *indebolire* il
  contenuto dell'audit ridurrebbe il valore di un controllo di conformità.

## Interazione con il diritto alla cancellazione (Art. 17)
`anonymize_user()` rende anonimi i dati identificativi dell'utente; le voci di audit
restano (pseudonimizzate via `user_id`/email pseudonimizzata) come obbligo legale di
conservazione delle evidenze di sicurezza. Il residuo di PII incidentale in note/titoli è
coperto dalla stessa base. Da formalizzare in `retention-and-erasure.md`.

## Raccomandazioni residue
1. Linea guida UI/operativa: non inserire nomi di persone in titoli/note dove non
   necessario (alimenta l'informativa al personale).
2. Rivalutare in DPIA il caso "ditta individuale" per `supplier.name` (nome = persona).
3. Mantenere la verifica AST come check periodico quando si aggiungono nuove `log_action`.
