# MANUAL_UTENTE.md — GRC Compliance Webapp

> Guida per utenti finali: Compliance Officer, Risk Manager, Plant Manager, Plant Security Officer, Auditor Esterno.

---

## Indice

- [Primo accesso](#primo-accesso)
- [Navigazione e interfaccia](#navigazione-e-interfaccia)
- [Ruoli e cosa puoi fare](#ruoli-e-cosa-puoi-fare)
- [Dashboard](#dashboard)
- [Gestione controlli (M03)](#gestione-controlli-m03)
- [Asset IT e OT (M04)](#asset-it-e-ot-m04)
- [Risk Assessment (M06)](#risk-assessment-m06)
- [Documenti ed evidenze (M07)](#documenti-ed-evidenze-m07)
- [Scadenzario e task (M08)](#scadenzario-e-task-m08)
- [Gestione incidenti (M09)](#gestione-incidenti-m09)
- [PDCA (M11)](#pdca-m11)
- [Lesson Learned (M12)](#lesson-learned-m12)
- [Audit Preparation (M17)](#audit-preparation-m17)
- [Reporting ed export (M18)](#reporting-ed-export-m18)
- [Formazione e awareness (M15)](#formazione-e-awareness-m15)
- [AI Engine — suggerimenti IA (M20)](#ai-engine--suggerimenti-ia-m20)
- [Notifiche e preferenze](#notifiche-e-preferenze)
- [Domande frequenti](#domande-frequenti)

---

## Primo accesso

### Login con SSO aziendale

1. Apri il browser e vai su `https://grc.azienda.com`
2. Clicca **Accedi con account aziendale**
3. Inserisci le credenziali del tuo account di dominio
4. Al primo accesso ti verrà chiesto di scegliere la lingua dell'interfaccia — puoi cambiarla in qualsiasi momento dal menu profilo in alto a destra

Se la tua azienda non usa SSO, usa le credenziali che ti sono state inviate via email dal Compliance Officer.

### Cambio lingua

Menu profilo (icona in alto a destra) → **Preferenze** → **Lingua interfaccia** → scegli tra Italiano, English, Français, Polski, Türkçe.

La lingua si applica immediatamente a tutta l'interfaccia, alle email di notifica e agli export PDF che genererai.

### Password e sessione

- La sessione scade dopo 8 ore di inattività
- Se usi SSO aziendale non è necessario gestire una password separata
- Per resettare la password locale: pagina di login → **Password dimenticata**

---

## Navigazione e interfaccia

### Menu principale (sidebar sinistra)

Il menu mostra solo le sezioni a cui hai accesso in base al tuo ruolo. Le voci principali sono:

- **Dashboard** — riepilogo task, scadenze, rischi e compliance
- **Compliance** — controlli M03, documenti M07, evidenze
- **Risk** — asset M04, BIA M05, risk assessment M06
- **Operazioni** — incidenti M09, task M08, PDCA M11
- **Governance** — organigramma M00, fornitori M14, formazione M15
- **Audit** — preparazione M17, reporting M18
- **Impostazioni** — solo per ruoli amministrativi

### Selettore plant

In alto, vicino al logo, trovi il selettore **Plant**. Se hai accesso a più plant o BU, usa questo menu per filtrare la vista. La voce "Tutti i plant" mostra una vista aggregata (solo per Compliance Officer e ruoli superiori).

### Icone di stato comuni

| Icona | Significato |
|-------|-------------|
| Verde / check | Compliant, completato, valido |
| Giallo / orologio | Parziale, in corso, in scadenza |
| Rosso / X | Gap, scaduto, critico |
| Grigio | Non valutato, N/A |
| Arancione / campana | Alert, richiede attenzione |

---

## Ruoli e cosa puoi fare

### Compliance Officer

Hai accesso completo a tutti i moduli per tutti i plant nel tuo scope. Sei responsabile di:

- Mantenere aggiornata la libreria controlli (M03)
- Coordinare il workflow documentale (M07)
- Monitorare task e scadenze di tutto il team (M08)
- Gestire gli incidenti NIS2 e le notifiche ACN (M09)
- Preparare la documentazione per gli audit (M17)
- Generare report per il management (M18)

### Risk Manager

Hai accesso completo ai moduli di risk. Sei responsabile di:

- Supervisionare il risk assessment IT e OT (M06)
- Validare la BIA e i valori ALE (M05)
- Avviare e monitorare i cicli PDCA (M11)
- Ricevere alert su rischi con score >= 15 (rossi)

### Plant Manager

Hai accesso al tuo plant. Sei responsabile di:

- Approvare i documenti di livello direzione (M07)
- Ricevere escalation su task critici scaduti
- Validare le decisioni di risk treatment (M05)
- Partecipare alla revisione di direzione (M13)

### Plant Security Officer

Hai accesso operativo al tuo plant. Sei responsabile di:

- Aggiornare lo stato dei controlli (M03)
- Caricare evidenze (M07)
- Compilare i risk assessment IT e OT (M06)
- Aprire e gestire incidenti (M09)
- Completare i task assegnati (M08)

### Auditor Esterno

Hai accesso in sola lettura con token temporaneo. Puoi:

- Consultare i controlli e il loro stato (M03)
- Scaricare documenti e evidenze (M07)
- Esportare l'evidence pack per il tuo audit (M17)
- Ogni tua azione viene registrata nell'audit trail

Il token ha una scadenza: trovi la data di scadenza in alto nell'interfaccia. Contatta il Compliance Officer se hai bisogno di una proroga.

---

## Dashboard

La dashboard è personalizzata per ruolo e plant. Mostra:

**Riquadro task:** i tuoi task aperti ordinati per scadenza. I task in rosso sono già scaduti, in arancione scadono entro 7 giorni. Cliccando su un task apri direttamente il modulo di origine.

**Heat map rischi:** la mappa 5×5 probabilità × impatto per il plant selezionato. I quadranti rossi (score >= 15) sono evidenziati. Clicca su un quadrante per vedere i rischi che lo compongono.

**Stato compliance:** barre di avanzamento per ogni framework attivo (TISAX, NIS2, ISO 27001). Mostra la percentuale di controlli in stato compliant rispetto al totale.

**Scadenze prossime:** le prossime 10 scadenze nei 30 giorni futuri — documenti in revisione, task ricorrenti, assessment fornitori.

**Incidenti aperti:** solo se hai accesso a M09. I timer NIS2 sono evidenziati in rosso quando il tempo residuo è inferiore a 2 ore.

---

## Gestione controlli (M03)

### Visualizzare i controlli

Vai su **Compliance → Libreria controlli**. Puoi filtrare per:
- Framework (TISAX, NIS2, ISO 27001)
- Dominio / categoria
- Stato (compliant, parziale, gap, N/A, non valutato)
- Plant

### Aggiornare lo stato di un controllo

1. Clicca sul controllo che vuoi aggiornare
2. Nella scheda del controllo trovi il campo **Stato** — clicca per aprire il selettore
3. Scegli lo stato corretto:
   - **Compliant**: il controllo è pienamente soddisfatto, hai un'evidenza valida
   - **Parziale**: il controllo è parzialmente implementato
   - **Gap**: il controllo non è implementato, è necessaria azione
   - **N/A**: il controllo non si applica al tuo contesto (richiede doppia approvazione e scade dopo 12 mesi per TISAX L3)
4. Aggiungi una nota di contesto (obbligatoria per gap e N/A)
5. Collega l'evidenza pertinente tramite il pulsante **Allega evidenza**
6. Salva

> Un controllo con evidenza scaduta torna automaticamente a "parziale" anche se l'hai impostato come compliant. Mantieni le evidenze aggiornate.

### Mappatura tra framework

Nella scheda del controllo trovi la sezione **Controlli equivalenti** — mostra i controlli di altri framework che coprono lo stesso requisito. Utile per evitare lavoro doppio.

---

## Asset IT e OT (M04)

### Aggiungere un asset IT

Vai su **Risk → Asset inventory → Nuovo asset IT**. Compila:

- **Nome / FQDN**: hostname o indirizzo IP
- **Sistema operativo** e **versione** (importante per il calcolo CVE)
- **Data EOL**: se il sistema è fuori supporto, il rischio viene automaticamente aumentato
- **Esposto su Internet**: flag critico — aumenta il profilo di rischio
- **Processi critici collegati**: seleziona dalla lista (vengono da M05)

### Aggiungere un asset OT

Vai su **Risk → Asset inventory → Nuovo asset OT**. In aggiunta ai campi comuni:

- **Livello Purdue** (0–5): posizione nella gerarchia di rete OT
- **Categoria**: PLC, SCADA, HMI, RTU, sensore
- **Aggiornabile**: se il sistema non può essere patchato, indica il motivo e la finestra di manutenzione

### Visualizzare le dipendenze

Nella scheda di un asset trovi il grafico delle dipendenze — mostra gli asset collegati e la propagazione della criticità. Se un processo critico dipende da un asset con score alto, la criticità si propaga verso l'alto.

---

## Risk Assessment (M06)

### Avviare una valutazione

Vai su **Risk → Risk Assessment → Nuova valutazione**. Seleziona:
- Il plant di riferimento
- Il tipo: **IT** oppure **OT**
- L'asset o il dominio da valutare

### Compilare il questionario IT

Il sistema ti guida su 4 dimensioni:

1. **Esposizione**: l'asset è su Internet? In DMZ? Isolato?
2. **CVE**: qual è il punteggio CVE massimo degli asset coinvolti?
3. **Minacce di settore**: ci sono minacce attive note per il settore automotive?
4. **Gap controlli**: quanti controlli rilevanti sono in stato gap o non valutato?

Per ciascuna dimensione scegli un valore da 1 (basso) a 5 (alto). Il sistema calcola automaticamente lo score totale e lo posiziona sulla heat map.

### Compilare il questionario OT

Le dimensioni OT sono 5:

1. **Purdue + connettività**: il sistema è connesso a reti IT o a Internet?
2. **Patchability**: il sistema può essere aggiornato? Con quale frequenza?
3. **Impatto fisico / safety**: un'interruzione o alterazione può causare danni fisici o di sicurezza?
4. **Segmentazione**: la zona OT è adeguatamente separata?
5. **Rilevabilità anomalie**: esiste un sistema di detection per comportamenti anomali?

### Interpretare il risultato

- **Score 1–7** (verde): rischio accettabile — monitoraggio periodico
- **Score 8–14** (giallo): rischio moderato — piano di mitigazione entro 90 giorni
- **Score 15–25** (rosso): rischio alto — escalation automatica a Risk Manager e Plant Manager, piano entro 15 giorni

Se il tuo piano di mitigazione non viene inserito entro 15 giorni da un rischio rosso, il sistema invia un'escalation al Compliance Officer.

---

## Documenti ed evidenze (M07)

### Tipi di contenuto

**Documento controllato**: policy, procedura, istruzione operativa. Segue un workflow obbligatorio di revisione e approvazione. Ogni versione è immutabile dopo approvazione.

**Evidenza**: screenshot, report di scan, log di sistema, certificati. Upload diretto, nessun workflow, ma richiede data di scadenza per i contenuti a tempo (log, scan, certificati).

### Caricare un documento

1. Vai su **Compliance → Documenti → Nuovo documento**
2. Seleziona il tipo (policy / procedura / istruzione)
3. Carica il file PDF
4. Compila: titolo, codice documento, framework di riferimento, owner, revisore, approvatore
5. Salva in bozza

Il documento entra automaticamente in stato **Bozza** e viene assegnato come task al revisore nominato.

### Workflow di approvazione

Il documento attraversa 3 fasi obbligatorie:

- **Redazione** → l'owner carica la versione e salva
- **Revisione** → il revisore legge, può aggiungere note strutturate oppure approvare. Se rifiuta, deve scrivere un commento che diventa parte del changelog
- **Approvazione direzione** → il Plant Manager o CISO approva. Dopo l'approvazione il documento è immutabile

Per aprire una nuova versione clicca **Nuova revisione** nella scheda del documento.

### Caricare un'evidenza

1. Vai sulla scheda del controllo che vuoi documentare
2. Clicca **Allega evidenza**
3. Carica il file e inserisci:
   - Descrizione breve
   - Data di scadenza (obbligatoria per log, scan, certificati)
   - Framework / controlli coperti

> Se carichi un'evidenza con data di scadenza, il sistema ti invierà un reminder 30 giorni prima e un alert alla scadenza. Un controllo con evidenza scaduta degrada automaticamente a "parziale".

---

## Scadenzario e task (M08)

### Visualizzare i miei task

Vai su **Operazioni → I miei task**. Puoi filtrare per:
- Priorità (critica, alta, media, bassa)
- Scadenza (oggi, questa settimana, questo mese)
- Modulo di origine (incidente, revisione documento, PDCA...)
- Plant

### Completare un task

1. Clicca sul task
2. Leggi la descrizione e il link all'entità di origine (es. il documento da approvare, il rischio da mitigare)
3. Esegui l'azione richiesta nel modulo collegato
4. Torna al task e clicca **Segna come completato**
5. Aggiungi una nota di chiusura (facoltativa ma consigliata per i task critici)

Alcuni task si chiudono automaticamente quando completi l'azione nel modulo origine — per esempio, approvando un documento il relativo task di approvazione si chiude da solo.

### Escalation automatica

Se non completi un task critico entro la scadenza:
- +7 giorni: il tuo responsabile riceve una notifica
- +14 giorni: il Compliance Officer riceve una notifica
- +30 giorni: il Super Admin e il CISO ricevono un'allerta e il KPI viene penalizzato

---

## Gestione incidenti (M09)

### Aprire un incidente

Vai su **Operazioni → Incidenti → Nuovo incidente**. Compila:

- **Plant coinvolto**: determina automaticamente il profilo NIS2
- **Titolo e descrizione**: cosa è successo, quando, come è stato rilevato
- **Asset coinvolti**: seleziona dall'inventario
- **Severità iniziale**: bassa / media / alta / critica (aggiornabile)

Subito dopo la creazione il sistema valuta se il plant è soggetto NIS2 e, se sì, avvia i timer ACN visibili in cima alla scheda dell'incidente.

### Timer NIS2

Se il plant è classificato come soggetto NIS2 (essenziale o importante) appariranno tre countdown:

- **T+24h — Early warning ACN**: notifica preliminare all'Autorità di riferimento
- **T+72h — Notifica completa**: notifica dettagliata con impatto e misure adottate
- **T+30gg — Report finale**: rapporto conclusivo con RCA

Il CISO ha 30 minuti dalla creazione dell'incidente per confermare o escludere l'obbligo di notifica. Se non risponde entro 30 minuti il sistema assume che la notifica sia dovuta.

### Inviare una notifica ACN

1. Clicca **Prepara notifica** nella scheda dell'incidente
2. Il form è precompilato con i dati disponibili (soggetto NIS2, settore, natura dell'incidente)
3. Integra i campi mancanti: impatto stimato, misure adottate, eventuale impatto cross-border
4. Il CISO o il CO firma digitalmente
5. Clicca **Invia notifica** — il sistema registra hash e timestamp

### Chiudere un incidente

Un incidente non può essere chiuso senza un'**analisi RCA** approvata. Per completare la RCA:

1. Nella scheda incidente vai alla sezione **Root Cause Analysis**
2. Scegli il metodo: 5 Why, Ishikawa, o testo libero
3. Compila causa radice, controlli falliti e azioni correttive
4. Salva e invia per approvazione al Risk Manager

Dopo l'approvazione dell'RCA puoi chiudere l'incidente. La chiusura genera automaticamente:
- Una lesson learned in M12
- Un task PDCA in M11 (se le azioni correttive sono strutturali)
- Un trigger di revisione sui documenti collegati in M07

---

## PDCA (M11)

### Cos'è un ciclo PDCA

Ogni ciclo PDCA rappresenta un'azione di miglioramento continuo su un controllo, un dominio o un obiettivo custom. Le 4 fasi sono:

- **Plan**: definisci l'obiettivo, le azioni e le risorse necessarie
- **Do**: esegui le azioni pianificate
- **Check**: verifica che i risultati corrispondano agli obiettivi
- **Act**: standardizza o correggi, poi riparti

### Avviare un ciclo PDCA

Vai su **Operazioni → PDCA → Nuovo ciclo**. In alternativa, i cicli PDCA vengono creati automaticamente da:
- Incidenti chiusi (M09) — fase ACT immediata
- Risk assessment con score rosso (M06) — fase PLAN urgente
- Audit finding (M17) — fase ACT
- Delibere della revisione di direzione (M13)

### Gestire le fasi

Per ogni fase clicca su **Apri fase** per vedere le azioni richieste. Ogni fase ha un output obbligatorio prima di poter avanzare alla successiva. Gli output tipici sono documenti, evidenze o task completati.

---

## Lesson Learned (M12)

### Consultare la knowledge base

Vai su **Governance → Knowledge base**. Puoi cercare per parola chiave, framework, tipo di controllo o plant. Vengono mostrate solo le lesson learned approvate.

### Creare una lesson learned manuale

1. Vai su **Governance → Lesson Learned → Nuova**
2. Compila: titolo, descrizione dell'evento, metodo di analisi, causa radice
3. Collega i controlli impattati
4. Definisci le azioni: **breve termine** (entro 30 giorni) e **strutturali** (via PDCA)
5. Invia per approvazione

### Ricevere una propagazione cross-plant

Se un tuo collega di un altro plant crea una lesson learned che il sistema ritiene rilevante per il tuo plant (stesso controllo, stessa tipologia asset o profilo di rischio simile), riceverai una notifica con la richiesta di valutazione.

Hai 30 giorni per rispondere:
- **Rilevante**: il sistema crea un task in M08 per adottare le azioni consigliate
- **Non rilevante**: inserisci la motivazione — viene registrata nell'audit trail
- **Già gestita**: collega la tua soluzione esistente

---

## Audit Preparation (M17)

### Verificare il readiness score

Vai su **Audit → Readiness**. Il punteggio (0–100%) è calcolato su:

- Percentuale di controlli compliant o parziali (con peso)
- Validità delle evidenze collegate
- Stato dei documenti (approvati vs in bozza)
- Task critici aperti (penalizzano il punteggio)

Un punteggio sotto il 70% genera un alert e blocca la pianificazione dell'audit. Il punteggio consigliato per procedere è 85%.

### Scaricare l'evidence pack

1. Vai su **Audit → Evidence pack → Genera**
2. Seleziona il framework (TISAX, NIS2, ISO 27001) e il plant
3. Il sistema costruisce uno ZIP strutturato per dominio con tutti i documenti e le evidenze valide
4. Se sei un auditor esterno, il Compliance Officer può generare il pack e condividere il link (scade dopo 48 ore)

### Gestire i finding di audit

Quando ricevi un finding da un auditor:

1. Vai su **Audit → Finding → Nuovo**
2. Inserisci: descrizione, severità, controllo collegato
3. Compila il **piano di risposta** con data target
4. Carica l'**evidenza di chiusura** quando hai risolto il finding
5. Un finding grave apre automaticamente un ciclo PDCA in M11

---

## Reporting ed export (M18)

### Dashboard reporting

Vai su **Audit → Reporting**. Trovi tre livelli di dashboard:

- **Operativa**: stato task, controlli per framework e plant, scadenze
- **Risk**: heat map aggregata, ALE totale, top 10 rischi aperti
- **Executive**: ALE in €, ROI delle misure, readiness %, trend maturità PDCA

### Generare un report PDF

1. Seleziona il tipo di report (gap TISAX, compliance NIS2, SOA ISO 27001, BIA executive)
2. Scegli il plant e il periodo
3. Seleziona la lingua del report
4. Clicca **Genera** — il PDF viene firmato con timestamp e hash
5. Il report è disponibile per il download nella sezione **Report generati**

Tutti i report generati sono registrati nell'audit trail.

---

## Formazione e awareness (M15)

### Verificare il proprio stato formazione

Vai su **Governance → Formazione → Il mio piano**. Trovi l'elenco dei corsi obbligatori per il tuo ruolo e plant, con stato di completamento e data di scadenza.

### Completare un corso

I corsi erogati via KnowBe4 si aprono direttamente dalla piattaforma GRC cliccando **Avvia corso**. I completamenti vengono sincronizzati automaticamente ogni notte — se hai completato un corso su KnowBe4 e non appare ancora come completato nella GRC, aspetta il giorno successivo o contatta il Compliance Officer.

### Risultati phishing simulation

Se partecipi a una campagna di phishing simulation gestita da KnowBe4, i risultati appaiono nella sezione **Awareness** del tuo profilo. Non vengono condivisi nominalmente fuori dal team HR/Security.

---

## AI Engine — suggerimenti IA (M20)

> Il modulo AI è abilitato solo se il tuo amministratore ha attivato questa funzione per il tuo plant.

### Come funziona

Quando il modulo AI è attivo, vedrai un riquadro **Suggerimento IA** in alcuni moduli — incidenti, asset, documenti, task. Il sistema analizza il contesto e propone:

- Una **classificazione suggerita** (es. severità incidente, criticità asset)
- Una **bozza di testo** (es. notifica ACN, policy, RCA)
- Un **alert proattivo** (es. task con alto rischio di slittamento)

### Cosa devi fare

Il suggerimento IA non ha effetto fino a quando non lo **confermi esplicitamente**. Puoi:

- **Accettare** il suggerimento così com'è — clicca **Usa questo suggerimento**
- **Modificare** il testo e poi cliccare **Usa versione modificata** — la tua versione sovrascrive quella dell'IA
- **Ignorare** il suggerimento e procedere manualmente — il riquadro si chiude senza effetti

> Ogni interazione (suggerimento ricevuto, testo finale adottato) viene registrata nell'audit trail per garantire la tracciabilità delle decisioni. L'IA non prende mai decisioni autonomamente.

---

## Notifiche e preferenze

### Tipi di notifica

Alcune notifiche sono obbligatorie e non disattivabili:

- Alert timer NIS2 (T+24h, T+72h, T+30gg)
- Escalation task critico
- Rischio con score rosso
- Scadenza delega normativa

Le notifiche configurabili includono digest giornaliero o settimanale, avvisi documenti in scadenza, nuovi task assegnati.

### Configurare le preferenze

Vai su **Profilo → Notifiche**:

- **Frequenza digest**: giornaliero o settimanale
- **Canale**: email (sempre attivo) e webhook se configurato
- **Moduli**: seleziona da quali moduli vuoi ricevere notifiche non obbligatorie

---

## Domande frequenti

**Non trovo un controllo che dovrebbe essere nel mio framework.**
Verifica di aver selezionato il plant corretto nel selettore in alto. Se il framework è attivo per quel plant ma il controllo non appare, contatta il Compliance Officer — potrebbe non essere stato generato durante l'attivazione del framework.

**Ho caricato un'evidenza ma il controllo mostra ancora "gap".**
Verifica che l'evidenza sia collegata al controllo corretto (scheda evidenza → sezione "Controlli coperti") e che la data di scadenza non sia già passata.

**Il timer NIS2 è partito ma l'incidente non è davvero un incidente NIS2.**
Il CISO ha 30 minuti per escludere l'obbligo di notifica. Se sei il CISO, apri la scheda incidente e clicca **Escludi obbligo NIS2** inserendo la motivazione. I timer si fermano e la decisione viene registrata nell'audit trail.

**Ho completato un task ma continua ad apparire come aperto.**
Alcuni task si chiudono automaticamente quando l'azione nel modulo origine è completata. Se il task è manuale, devi chiuderlo esplicitamente dalla scheda del task → **Segna come completato**.

**Un documento che avevo approvato risulta ora "in revisione".**
È stato attivato un trigger di revisione straordinaria — probabilmente collegato a un incidente, un finding di audit o un cambio normativo. Controlla le note nella scheda del documento per capire il motivo.

**Non riesco ad impostare un controllo come N/A.**
Per i controlli TISAX L3 lo stato N/A richiede la firma di almeno due ruoli (doppio lock). Se sei il primo ad approvare, il controllo rimane in attesa della seconda firma. Se sei l'unico proprietario, contatta il CISO per la co-firma.

**Il suggerimento IA non appare più.**
Il modulo AI potrebbe essere stato disabilitato dall'amministratore per il tuo plant, oppure la funzione specifica non è attiva. Contatta il Compliance Officer o il System Administrator.
