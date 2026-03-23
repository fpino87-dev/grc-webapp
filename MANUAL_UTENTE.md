# Manuale Utente — GRC Platform

> Guida per utenti finali: Compliance Officer, Risk Manager, Plant Manager, Plant Security Officer, Auditor Esterno.

---

## Indice

- [1. Accesso e navigazione](#1-accesso-e-navigazione)
- [2. Dashboard](#2-dashboard)
- [3. Gestione Controlli (M03)](#3-gestione-controlli-m03)
- [4. Asset IT e OT (M04)](#4-asset-it-e-ot-m04)
- [5. Business Impact Analysis (M05)](#5-business-impact-analysis-m05)
- [6. Risk Assessment (M06)](#6-risk-assessment-m06)
- [7. Documenti ed Evidenze (M07)](#7-documenti-ed-evidenze-m07)
- [8. Gestione Incidenti (M09)](#8-gestione-incidenti-m09)
- [9. PDCA (M11)](#9-pdca-m11)
- [10. Lesson Learned (M12)](#10-lesson-learned-m12)
- [11. Revisione Direzione (M13)](#11-revisione-direzione-m13)
- [12. Audit Preparation (M17)](#12-audit-preparation-m17)
- [13. Fornitori (M14)](#13-fornitori-m14)
- [14. Formazione (M15)](#14-formazione-m15)
- [15. Business Continuity (M16)](#15-business-continuity-m16)
- [16. Activity Schedule (Scadenzario)](#16-activity-schedule-scadenzario)
- [17. Documenti Obbligatori](#17-documenti-obbligatori)
- [18. Notifiche Email](#18-notifiche-email)
- [19. Governance (M00)](#19-governance-m00)
- [20. Impostazioni (solo Admin)](#20-impostazioni-solo-admin)
- [Ruoli e cosa puoi fare](#ruoli-e-cosa-puoi-fare)
- [AI Engine — suggerimenti IA (M20)](#ai-engine--suggerimenti-ia-m20)
- [Reporting ed export (M18)](#reporting-ed-export-m18)
- [Appendice: Domande frequenti](#appendice-domande-frequenti)

---

## 1. Accesso e navigazione

### Login con email e password

[Schermata: pagina di login]

1. Apri il browser e vai su `https://grc.azienda.com`
2. Inserisci la tua **email aziendale** nel primo campo
3. Inserisci la **password** nel secondo campo (minimo 12 caratteri)
4. Clicca **Accedi**
5. Al primo accesso ti verrà chiesto di cambiare la password temporanea ricevuta via email

Se utilizzi SSO aziendale, clicca invece **Accedi con account aziendale** e inserisci le credenziali del tuo account di dominio.

> La sessione rimane attiva per 30 minuti di inattività. Dopo la scadenza ti viene chiesto di reinserire la password. Il token di sessione si rinnova automaticamente durante l'uso attivo.

Per reimpostare la password: dalla pagina di login clicca **Password dimenticata** e inserisci la tua email. Riceverai un link valido per 15 minuti.

### Selezione sito (plant) in alto a sinistra

[Schermata: selettore plant nella topbar]

Subito dopo il login, in alto a sinistra vicino al logo, trovi il **selettore plant**. Se hai accesso a più stabilimenti o business unit:

1. Clicca sul nome del plant attuale (o su "Seleziona plant" al primo accesso)
2. Appare un menu a tendina con tutti i plant nel tuo scope
3. Clicca sul plant che vuoi visualizzare — la pagina si aggiorna immediatamente

La voce **Tutti i plant** mostra una vista aggregata di tutti gli stabilimenti. Questa opzione è disponibile solo per Compliance Officer e ruoli con accesso multi-plant.

Tutte le operazioni (creazione asset, apertura incidenti, valutazione controlli) vengono associate al plant selezionato in quel momento.

### Cambio lingua (IT/EN) in alto a destra

[Schermata: menu lingua nella topbar]

1. Clicca sull'icona della lingua (o sulla sigla della lingua corrente) in alto a destra
2. Seleziona la lingua desiderata: **Italiano**, **English**, **Français**, **Polski**, **Türkçe**
3. L'interfaccia si aggiorna immediatamente senza ricaricare la pagina

La lingua selezionata si applica a tutta l'interfaccia. I report PDF generati utilizzano la lingua attiva al momento della generazione.

### Menu laterale: sezioni principali e cosa contengono

[Schermata: sidebar con menu espanso]

Il menu laterale a sinistra mostra solo le sezioni accessibili in base al tuo ruolo. Le voci principali sono:

| Voce | Cosa contiene |
|------|--------------|
| **Dashboard** | KPI compliance, heat map rischi, scadenze imminenti, alert |
| **Compliance** | Libreria controlli (M03), documenti (M07), evidenze |
| **Risk** | Asset IT/OT (M04), BIA (M05), Risk Assessment (M06) |
| **Operazioni** | Incidenti (M09), Task/Scadenzario (M08), PDCA (M11) |
| **Governance** | Organigramma/Ruoli (M00), Lesson Learned (M12), Revisione Direzione (M13), Fornitori (M14), Formazione (M15), BCP (M16) |
| **Audit** | Audit Preparation (M17), Reporting (M18) |
| **Notifiche** | Notifiche email, preferenze |
| **Impostazioni** | Solo per ruoli amministrativi — SMTP, policy, profili notifica |

Per espandere o comprimere una sezione clicca sul titolo della voce. Lo stato del menu viene ricordato tra una sessione e l'altra.

### Icona ? su ogni pagina per aiuto contestuale

[Schermata: pulsante ? accanto al titolo della pagina]

In quasi tutte le pagine operative trovi un piccolo pulsante **`?`** vicino al titolo del modulo. Cliccandolo si apre un pannello laterale con:

- Una spiegazione breve di cosa fa il modulo
- I passi tipici da seguire
- Le connessioni con altri moduli (es. quali task o PDCA vengono creati automaticamente)
- L'elenco di prerequisiti consigliati ("Prima di iniziare")

Usa il pannello di help per orientarti su moduli che usi meno spesso o quando introduci il sistema a nuovi colleghi.

### Bottoni Manuale Utente e Manuale Tecnico nella barra in basso

[Schermata: barra inferiore con bottoni manuale]

In fondo a ogni pagina, nella barra in basso, trovi due pulsanti fissi:

- **Manuale Utente** (icona libro): apre questo manuale in una nuova scheda
- **Manuale Tecnico** (icona chiave inglese): apre il manuale tecnico con dettagli architetturali, visibile solo ai profili con accesso amministrativo

Entrambi i pulsanti sono sempre visibili indipendentemente dal modulo in cui ti trovi.

---

## 2. Dashboard

[Schermata: dashboard principale]

La dashboard è la prima pagina che vedi dopo il login. Il contenuto è personalizzato per il tuo ruolo e il plant selezionato.

### Cosa mostrano i KPI principali

In cima alla dashboard trovi 4 riquadri con i KPI principali:

| KPI | Cosa misura |
|-----|------------|
| **Compliance %** | Percentuale di controlli in stato "compliant" o "parziale con evidenza valida" rispetto al totale dei controlli attivi per il framework selezionato |
| **Rischi aperti** | Numero di risk assessment con stato "aperto" (non accettati e non chiusi). Il numero è accompagnato dal conteggio dei rischi critici (score > 14) in rosso |
| **Incidenti** | Incidenti aperti nel plant selezionato. I numeri in rosso indicano incidenti con timer NIS2 attivi |
| **Task scaduti** | Task assegnati al tuo ruolo (o a tutta la tua organizzazione se sei CO) con data di scadenza già superata |

### Come interpretare i colori

La piattaforma usa una convenzione cromatica coerente su tutta l'interfaccia:

- **Verde**: tutto in ordine — compliant, completato, valido, nei tempi
- **Giallo**: attenzione richiesta — parziale, in scadenza entro 30 giorni, in corso
- **Rosso**: critico — gap, scaduto, rischio alto (score > 14), timer NIS2 in scadenza
- **Grigio**: non valutato, N/A, archiviato
- **Arancione**: alert o avviso — richiede attenzione ma non è ancora critico

Questi colori si applicano a badge di stato, barre di avanzamento, indicatori nella heat map e icone nella sidebar.

### Widget prossime scadenze

[Schermata: widget scadenze nella dashboard]

Il widget "Prossime scadenze" mostra le prime 10 scadenze nei successivi 30 giorni. Per ogni scadenza vedi:

- Il tipo (documento, evidenza, task, assessment fornitore, ecc.)
- Il nome dell'elemento
- La data di scadenza con colore giallo (< 30 giorni) o rosso (< 7 giorni)

Cliccando su una scadenza vieni portato direttamente alla pagina dell'elemento interessato.

### Alert ruoli vacanti

Se ci sono ruoli normativi obbligatori senza un titolare assegnato (es. CISO non nominato, DPO vacante), nella dashboard appare un banner arancione "Ruoli vacanti" con il conteggio e un link alla pagina di governance (M00). Questi alert impattano negativamente il KPI di compliance.

### Come navigare direttamente a un elemento dal dashboard

Ogni elemento interattivo nella dashboard è cliccabile:

- Clicca su un task scaduto per aprire la scheda del task
- Clicca su un quadrante della heat map per vedere i rischi in quella zona
- Clicca su una barra di compliance per andare alla libreria controlli filtrata per quel framework
- Clicca su un incidente per aprire la scheda incidente

---

## 3. Gestione Controlli (M03)

[Schermata: libreria controlli]

### Come valutare un controllo

1. Vai su **Compliance → Libreria controlli**
2. Usa i filtri (framework, dominio, stato, plant) per trovare il controllo che ti interessa
3. Clicca sul nome del controllo per aprire la scheda
4. Nel campo **Stato** clicca per aprire il selettore e scegli lo stato appropriato
5. Aggiungi una nota di contesto nel campo **Note valutazione** (obbligatoria per Gap e N/A)
6. Collega l'evidenza tramite il pulsante **Allega evidenza**
7. Clicca **Salva**

### Differenza tra Compliant, Parziale, Gap, N/A

| Stato | Quando usarlo |
|-------|--------------|
| **Compliant** | Il controllo è pienamente soddisfatto. Hai un'evidenza valida e non scaduta che lo dimostra |
| **Parziale** | Il controllo è implementato solo in parte. C'è un piano per completarlo ma i requisiti non sono ancora tutti soddisfatti |
| **Gap** | Il controllo non è implementato. E' necessaria un'azione correttiva. Genera automaticamente un task |
| **N/A** | Il controllo non si applica al contesto del tuo plant. Richiede una nota obbligatoria. Per TISAX L3 richiede la firma di due ruoli e scade dopo 12 mesi |

> Un controllo con evidenza scaduta torna automaticamente a "Parziale" anche se lo hai impostato come Compliant. Mantieni le evidenze aggiornate.

### Come caricare un'evidenza

1. Dalla scheda del controllo clicca **Allega evidenza**
2. Clicca **Scegli file** e seleziona il file dal tuo computer (formati accettati: PDF, DOCX, XLSX, PNG, JPG, ZIP — dimensione massima 50 MB)
3. Compila:
   - **Descrizione breve** (es. "Screenshot configurazione firewall del 15/03/2026")
   - **Data di scadenza** — obbligatoria per log di sistema, report di scan, certificati. Lascia vuota per documenti senza scadenza
   - **Framework / controlli coperti** — seleziona tutti i controlli che questa evidenza documenta
4. Clicca **Carica**

L'evidenza è disponibile immediatamente. Il sistema verificherà automaticamente che il tipo MIME del file corrisponda all'estensione dichiarata.

### Come scaricare SOA ISO 27001, VDA ISA TISAX, NIS2 Matrix

[Schermata: pagina export compliance]

1. Vai su **Compliance → Libreria controlli**
2. Clicca il pulsante **Esporta** (icona download) in alto a destra nella pagina
3. Seleziona il tipo di export:
   - **SOA ISO 27001** — Statement of Applicability con tutti i controlli Annex A e il relativo stato
   - **VDA ISA TISAX** — Tabella VDA Information Security Assessment
   - **NIS2 Matrix** — Matrice di conformità NIS2

> **Nota importante**: usa sempre il pulsante "Esporta" all'interno della pagina. Non aprire l'URL del file direttamente dal browser copiando il link — il download richiede il token JWT della sessione attiva e fallirebbe con un errore 401 se tentato fuori dalla piattaforma.

### Gap Analysis tra framework

1. Vai su **Compliance → Gap Analysis**
2. Seleziona i due framework da confrontare (es. ISO 27001 vs TISAX L2)
3. Il sistema mostra una tabella con i controlli mappati tra i due framework, evidenziando:
   - Controlli soddisfatti in entrambi i framework (verde)
   - Controlli soddisfatti in uno solo dei due (giallo)
   - Controlli in gap in entrambi (rosso)
4. Puoi esportare la gap analysis in formato Excel

---

## 4. Asset IT e OT (M04)

[Schermata: inventario asset]

### Come inserire un asset

**Asset IT:**

1. Vai su **Risk → Asset inventory → Nuovo asset IT**
2. Compila i campi obbligatori:
   - **Nome / FQDN**: hostname o indirizzo IP
   - **Sistema operativo** e **versione**
   - **Data EOL**: se il sistema è fuori supporto la criticità viene aumentata automaticamente
   - **Esposto su Internet**: flag critico — aumenta il profilo di rischio
   - **Livello di criticità**: da 1 a 5 (vedi tabella sotto)
3. Nella sezione **Processi critici collegati** seleziona i processi dalla BIA (M05) che dipendono da questo asset
4. Clicca **Salva**

**Asset OT:**

1. Vai su **Risk → Asset inventory → Nuovo asset OT**
2. In aggiunta ai campi comuni degli asset IT, compila:
   - **Livello Purdue** (0–5): posizione nella gerarchia di rete OT
   - **Categoria**: PLC, SCADA, HMI, RTU, sensore, altro
   - **Aggiornabile**: se il sistema non può essere patchato, indica il motivo e la finestra di manutenzione programmata
3. Clicca **Salva**

### Differenza tra asset IT e OT

| Caratteristica | Asset IT | Asset OT |
|---------------|---------|---------|
| Esempi | Server, workstation, firewall, switch, applicazioni | PLC, SCADA, HMI, RTU, sensori industriali |
| Rete tipica | Rete aziendale, Internet | Rete di produzione, bus di campo |
| Patching | Frequente, automatizzabile | Limitato, richiede finestre di manutenzione |
| Impatto interruzione | Perdita di dati, indisponibilità servizio | Fermo produzione, danni fisici, rischio safety |
| Risk assessment | Dimensioni esposizione/CVE | Dimensioni Purdue/patchability/safety |

### Tabella criticità 1-5

Nel form di creazione e modifica asset trovi un badge di criticità con tooltip esplicativi per ogni livello. Come riferimento:

| Livello | Etichetta | Descrizione |
|---------|-----------|-------------|
| **1** | Bassa | Fermo o compromissione non impatta la produzione. Perdita accettabile senza piano di continuità dedicato |
| **2** | Medio-bassa | Impatto limitato a funzioni amministrative o di supporto. Ripristino entro 24 ore |
| **3** | Media | Impatto su processi operativi. Richiede piano di continuità. Perdita di dati o di produzione misurabile |
| **4** | Alta | Fermo causa perdita economica rilevante, impatto su clienti o su conformità normativa. RTO < 4 ore |
| **5** | Critica | Impatto safety, rischio vita o danni fisici, oppure fermo totale della produzione. RTO < 1 ora. Richiede analisi rischio immediata |

Usa sempre questa tabella per garantire coerenza tra plant diversi.

### Come registrare un change esterno

Quando un asset subisce una modifica significativa (aggiornamento firmware, cambio configurazione, ampliamento perimetro di rete):

1. Apri la scheda dell'asset
2. Clicca **Registra change** nella sezione "Storico modifiche"
3. Compila: data del change, descrizione, tipo (configurazione / hardware / software / rete), impatto stimato
4. Salva — il change viene registrato nell'audit trail e l'asset riceve il badge "Da rivalutare"

### Badge "Da rivalutare" — quando appare e cosa fare

Il badge arancione **"Da rivalutare"** appare sulla scheda dell'asset quando:

- E' stato registrato un change esterno
- E' scaduta la data di revisione periodica prevista dalla policy
- Un rischio collegato all'asset è cambiato di score significativamente
- L'asset ha raggiunto la data EOL del sistema operativo

Cosa fare: apri la scheda dell'asset, verifica che le informazioni siano ancora accurate (in particolare criticità, esposizione e processi critici collegati), poi clicca **Segna come rivalutato**. Se necessario aggiorna i campi prima di confermare.

---

## 5. Business Impact Analysis (M05)

[Schermata: lista processi BIA]

### Come creare un processo critico

1. Vai su **Risk → BIA → Nuovo processo**
2. Compila:
   - **Nome del processo**: es. "Gestione ordini di produzione"
   - **Descrizione**: cosa fa il processo, chi lo utilizza
   - **Owner del processo**: seleziona il ruolo responsabile
   - **Reparto / funzione**: area aziendale di riferimento
   - **Plant**: stabilimento di riferimento
3. Salva — il processo entra in stato **Bozza**

### MTPD, RTO, RPO — spiegazione semplice con esempi

Questi tre parametri definiscono la tolleranza del processo all'interruzione:

| Parametro | Definizione | Esempio pratico |
|-----------|-------------|----------------|
| **MTPD** (Maximum Tolerable Period of Disruption) | Per quanto tempo il processo può essere fermo prima che l'azienda subisca danni irreversibili | Es. "Il processo di spedizione può essere fermo al massimo 48 ore prima di perdere clienti chiave" |
| **RTO** (Recovery Time Objective) | In quanto tempo dobbiamo ripristinare il processo dopo un'interruzione | Es. "Il sistema MES deve tornare operativo entro 4 ore dall'incidente" |
| **RPO** (Recovery Point Objective) | Fino a quale punto nel passato possiamo perdere i dati senza danni accettabili | Es. "Non possiamo perdere più di 1 ora di dati di produzione" — quindi i backup devono essere almeno ogni ora |

Il sistema usa RTO e RPO per verificare che il piano BCP collegato (M16) sia coerente: se il BCP prevede un RTO superiore a quello dichiarato nella BIA, appare un avviso.

### Flusso: bozza → validazione → approvazione

1. **Bozza**: il processo è stato creato ma non ancora validato. Puoi modificare tutti i campi
2. **Validazione**: il Risk Manager verifica i parametri MTPD/RTO/RPO e li approva o richiede modifiche
3. **Approvazione**: il Plant Manager approva formalmente. Il processo diventa immutabile — per modificarlo è necessario aprire una nuova revisione

Per avanzare di fase: dalla scheda del processo clicca **Invia per validazione** (da Bozza) o **Invia per approvazione** (da Validazione).

### Come collegare un processo a un asset

1. Apri la scheda del processo BIA
2. Nella sezione **Asset dipendenti** clicca **Aggiungi asset**
3. Cerca e seleziona l'asset dall'inventario (M04)
4. Indica il tipo di dipendenza: **Critica** (il processo si ferma senza questo asset) o **Supporto** (degrado delle prestazioni)
5. Salva

La dipendenza è bidirezionale: l'asset mostrerà nella propria scheda i processi che dipendono da lui, e la criticità del processo influenza il calcolo del rischio sull'asset.

---

## 6. Risk Assessment (M06)

[Schermata: risk assessment list]

### Differenza rischio inerente vs residuo

- **Rischio inerente**: il livello di rischio in assenza di qualsiasi controllo. Rappresenta la minaccia "grezza" sull'asset o sul dominio
- **Rischio residuo**: il livello di rischio dopo aver applicato i controlli esistenti. E' il valore su cui si basa la decisione di accettare o trattare il rischio

Nel form di valutazione compili prima il rischio inerente, poi il sistema calcola automaticamente il residuo in base allo stato dei controlli collegati. Se i controlli non sono ancora sufficienti il residuo rimane alto.

### Come compilare le dimensioni IT e OT

**Dimensioni risk assessment IT (4 assi):**

1. **Esposizione**: l'asset è su Internet? In DMZ? Isolato? (1 = completamente isolato, 5 = esposto su Internet senza protezioni)
2. **CVE**: qual è il punteggio CVE massimo degli asset coinvolti? (1 = nessuna vulnerabilità nota, 5 = CVE critica non patchata)
3. **Minacce di settore**: ci sono minacce attive note per il settore automotive? (1 = nessuna, 5 = campagna attiva documentata)
4. **Gap controlli**: quanti controlli rilevanti sono in stato gap o non valutato? (1 = tutti compliant, 5 = maggioranza in gap)

**Dimensioni risk assessment OT (5 assi):**

1. **Purdue + connettività**: il sistema è connesso a reti IT o a Internet? (1 = livello 0 isolato, 5 = connesso a Internet)
2. **Patchability**: il sistema può essere aggiornato? Con quale frequenza? (1 = patch regolari, 5 = mai aggiornabile)
3. **Impatto fisico / safety**: un'interruzione o alterazione può causare danni fisici o di sicurezza sul lavoro? (1 = nessun impatto fisico, 5 = rischio per l'incolumità delle persone)
4. **Segmentazione**: la zona OT è adeguatamente separata da IT e da Internet? (1 = completamente segregata, 5 = flat network)
5. **Rilevabilità anomalie**: esiste un sistema di detection per comportamenti anomali? (1 = IDS/ICS dedicato attivo, 5 = nessuna visibilità)

### Soglia critica (score > 14) e task automatici generati

Quando il **rischio residuo supera 14** (quadranti rossi della heat map 5x5):

- Il Risk Manager e il Plant Manager ricevono una notifica immediata
- Viene creato automaticamente un task di pianificazione trattamento rischio con scadenza 15 giorni
- Se il task non viene completato entro 15 giorni, parte un'escalation al Compliance Officer
- Il rischio viene evidenziato in rosso nella dashboard e nella heat map

### Accettazione formale del rischio

Se il rischio residuo è noto ma si decide di accettarlo (es. costo del trattamento superiore all'impatto atteso):

1. Dalla scheda del rischio clicca **Accetta rischio**
2. Compila il modulo di accettazione formale:
   - Motivazione (obbligatoria, min 50 caratteri)
   - Data di revisione (obbligatoria — il rischio deve essere rivalutato periodicamente)
   - Firma digitale del responsabile autorizzato
3. Salva — il rischio passa a stato "Accettato" e non genera più alert fino alla data di revisione

### Heat map e interpretazione

[Schermata: heat map 5x5]

La heat map mostra i rischi su una griglia Probabilita x Impatto 5x5:

- **Verde** (score 1-7): rischio accettabile — monitoraggio periodico
- **Giallo** (score 8-14): rischio moderato — piano di mitigazione entro 90 giorni
- **Rosso** (score 15-25): rischio alto — escalation automatica, piano entro 15 giorni

Clicca su un quadrante per vedere l'elenco dei rischi che lo compongono. Usa il filtro plant per confrontare la distribuzione dei rischi tra stabilimenti diversi.

---

## 7. Documenti ed Evidenze (M07)

[Schermata: gestione documenti]

### Differenza tra Documento e Evidenza

| Caratteristica | Documento | Evidenza |
|---------------|-----------|---------|
| Cosa rappresenta | Policy, procedura, istruzione operativa | Screenshot, log, report di scan, certificati |
| Workflow obbligatorio | Si — redazione, revisione, approvazione | No — upload diretto |
| Versioning | Si — ogni versione è immutabile dopo approvazione | No |
| Data di scadenza | Solo se esplicitamente configurata | Obbligatoria per log, scan, certificati |
| Uso principale | Dimostrare che un processo esiste e e' governato | Dimostrare che un controllo e' attivo e funzionante |

### Workflow approvazione documenti (3 livelli)

Il documento attraversa 3 fasi obbligatorie in sequenza:

1. **Redazione** (owner del documento): carica il file PDF, compila i metadati (titolo, codice, framework, owner, revisore, approvatore), salva in bozza. Il documento è modificabile solo in questa fase
2. **Revisione** (revisore nominato): legge il documento, può aggiungere note strutturate o approvare. Se rifiuta deve scrivere un commento che diventa parte del changelog permanente
3. **Approvazione direzione** (Plant Manager o CISO): approva formalmente. Dopo l'approvazione il documento è immutabile — per modificarlo devi aprire una nuova revisione tramite il pulsante **Nuova revisione**

### Come collegare un'evidenza a un controllo

Metodo 1 — dalla scheda del controllo:
1. Vai sulla scheda del controllo (Compliance → Libreria controlli → seleziona controllo)
2. Clicca **Allega evidenza** nella sezione "Evidenze collegate"
3. Carica il file o seleziona un'evidenza già caricata dal tuo archivio
4. Salva

Metodo 2 — dalla scheda dell'evidenza:
1. Carica l'evidenza tramite **Compliance → Evidenze → Nuova evidenza**
2. Nel campo **Controlli coperti** seleziona uno o piu' controlli che questa evidenza documenta
3. Salva

Un'evidenza puo' coprire piu' controlli contemporaneamente, anche di framework diversi.

### Scadenza evidenze e badge colorati

Le evidenze con data di scadenza mostrano un badge colorato nella scheda del controllo e nell'elenco evidenze:

| Badge | Significato |
|-------|-------------|
| **Verde** | Evidenza valida — scadenza a piu' di 30 giorni |
| **Giallo** | In scadenza — mancano meno di 30 giorni |
| **Rosso** | Scaduta — la data di scadenza e' gia' passata. Il controllo collegato degrada automaticamente a "Parziale" |
| **Grigio** | Nessuna data di scadenza impostata |

Il sistema invia un reminder via email 30 giorni prima della scadenza e un alert alla scadenza effettiva.

### Versioning documenti

Ogni documento approvato riceve un numero di versione (es. v1.0, v1.1, v2.0). Lo storico completo di tutte le versioni e' accessibile dalla scheda del documento nella sezione **Cronologia versioni**. Ogni versione registra:

- Data di approvazione
- Nome dell'approvatore
- Changelog (note del revisore)
- Hash del file per garantire l'integrita'

---

## 8. Gestione Incidenti (M09)

[Schermata: lista incidenti]

### Come aprire un incidente

1. Vai su **Operazioni → Incidenti → Nuovo incidente**
2. Compila i campi obbligatori:
   - **Plant coinvolto**: determina automaticamente il profilo NIS2 del soggetto
   - **Titolo**: descrizione sintetica (es. "Accesso non autorizzato al sistema MES — stabilimento Nord")
   - **Descrizione**: cosa e' successo, quando e' stato rilevato, come e' stato scoperto
   - **Asset coinvolti**: seleziona dall'inventario (M04)
   - **Severita' iniziale**: Bassa / Media / Alta / Critica — aggiornabile in qualsiasi momento
3. Clicca **Crea incidente**

Immediatamente dopo la creazione il sistema valuta se il plant e' soggetto NIS2 e, in caso affermativo, avvia i timer ACN visibili in cima alla scheda dell'incidente.

### Flag NIS2 e timer 24h (notifica ACN)

[Schermata: scheda incidente con timer NIS2]

Se il plant e' classificato come soggetto NIS2 (essenziale o importante), nella scheda dell'incidente appaiono tre countdown:

- **T+24h — Early warning ACN**: notifica preliminare all'Autorita' di riferimento (obbligo di legge)
- **T+72h — Notifica completa**: notifica dettagliata con impatto e misure adottate
- **T+30gg — Report finale**: rapporto conclusivo con RCA

Il CISO ha 30 minuti dalla creazione dell'incidente per confermare o escludere l'obbligo di notifica tramite il pulsante **Escludi obbligo NIS2**. Se non risponde entro 30 minuti il sistema assume che la notifica sia dovuta e i timer rimangono attivi.

I timer vengono visualizzati con sfondo rosso quando il tempo residuo e' inferiore a 2 ore.

### Compilazione RCA (Root Cause Analysis)

1. Nella scheda incidente vai alla sezione **Root Cause Analysis**
2. Scegli il metodo di analisi:
   - **5 Why**: guidato, con 5 livelli di "perche'"
   - **Ishikawa**: diagramma causa-effetto per categoria (Persone, Processo, Tecnologia, Ambiente)
   - **Testo libero**: narrativo non strutturato
3. Compila causa radice, controlli falliti e azioni correttive proposte
4. Invia per approvazione al Risk Manager tramite **Invia per approvazione**

Un incidente non puo' essere chiuso senza un'RCA approvata.

### Chiusura e PDCA automatico generato

Dopo l'approvazione dell'RCA puoi chiudere l'incidente tramite il pulsante **Chiudi incidente**. La chiusura genera automaticamente:

- Una **Lesson Learned** in M12 con le informazioni dell'incidente e le azioni correttive
- Un ciclo **PDCA** in M11 se le azioni correttive sono strutturali (es. modifica di procedure, implementazione di nuovi controlli)
- Un trigger di **revisione** sui documenti collegati in M07 se i controlli falliti sono coperti da policy esistenti

---

## 9. PDCA (M11)

[Schermata: lista cicli PDCA]

### Le 4 fasi: PLAN, DO, CHECK, ACT

Ogni ciclo PDCA rappresenta un'azione di miglioramento continuo. Le 4 fasi seguono una sequenza obbligatoria:

- **PLAN**: definisci l'obiettivo, le azioni da intraprendere e le risorse necessarie
- **DO**: esegui le azioni pianificate
- **CHECK**: verifica che i risultati corrispondano agli obiettivi attraverso un'evidenza misurabile
- **ACT**: standardizza la soluzione se ha funzionato, oppure riparte da DO con un approccio diverso

### Cosa serve per avanzare ogni fase

| Transizione | Requisito obbligatorio |
|-------------|----------------------|
| **PLAN → DO** | Descrizione dell'azione da eseguire (minimo 20 caratteri). Il piano deve essere comprensibile anche fuori contesto |
| **DO → CHECK** | Evidenza allegata che documenta l'azione eseguita (file obbligatorio) |
| **CHECK → ACT** | Risultato della verifica (testo descrittivo) + Esito scelto: **ok** / **parziale** / **ko** |
| **ACT → CHIUSO** | Standardizzazione: documentazione della soluzione adottata perche' sia replicabile (minimo 20 caratteri) |

### Cosa succede se esito CHECK = ko

Se nella fase CHECK l'esito e' **ko** (la soluzione non ha funzionato):

1. Il ciclo non avanza ad ACT ma torna automaticamente alla fase **DO**
2. Viene aggiunta una nota nel log del ciclo con la data del fallimento
3. E' necessario compilare un nuovo piano d'azione per la fase DO
4. Il contatore di cicli DO viene incrementato per tracciare quante iterazioni sono state necessarie

Non c'e' un limite al numero di iterazioni DO-CHECK, ma il sistema segnala cicli con piu' di 3 iterazioni al Compliance Officer.

### PDCA creati automaticamente da incidenti, finding, rischi critici

I cicli PDCA vengono creati manualmente o automaticamente da:

- **Incidenti chiusi (M09)**: quando le azioni correttive dell'RCA sono strutturali — fase di partenza PLAN
- **Finding di audit (M17)**: per Major NC e Minor NC — fase di partenza PLAN con scadenza determinata dalla severita'
- **Rischi con score > 14 (M06)**: quando il piano di trattamento richiede azioni strutturali — fase PLAN urgente
- **Delibere della revisione di direzione (M13)**: per ogni azione approvata dalla revisione — fase PLAN

In tutti i casi di creazione automatica il ciclo PDCA riporta il riferimento all'entita' di origine (es. "Incidente #INC-2026-042") e l'eventuale scadenza derivante dalla policy.

---

## 10. Lesson Learned (M12)

[Schermata: knowledge base lesson learned]

### Come creare una lesson learned manuale

1. Vai su **Governance → Lesson Learned → Nuova**
2. Compila:
   - **Titolo**: descrizione sintetica dell'evento o dell'apprendimento
   - **Descrizione dell'evento**: cosa e' successo, contesto, rilevanza
   - **Metodo di analisi utilizzato**: 5 Why, Ishikawa, testo libero
   - **Causa radice identificata**
   - **Controlli impattati**: seleziona i controlli rilevanti dalla libreria
   - **Azioni breve termine**: azioni da completare entro 30 giorni
   - **Azioni strutturali**: azioni di lungo periodo (verranno gestite via PDCA)
3. Clicca **Invia per approvazione**

Il Risk Manager o il Compliance Officer approvano la lesson learned prima che diventi visibile a tutta l'organizzazione nella knowledge base.

### Lesson learned create automaticamente da PDCA chiusi

Quando un ciclo PDCA viene chiuso con esito positivo, il sistema crea automaticamente una lesson learned che include:

- Il contesto originale (incidente, finding, rischio) che ha avviato il PDCA
- Le azioni eseguite nelle fasi DO
- Il risultato ottenuto nella fase CHECK
- La standardizzazione documentata nella fase ACT

La lesson learned automatica parte in stato "Bozza" e viene assegnata come task all'owner del ciclo PDCA per la revisione prima dell'approvazione.

### Ricerca nella knowledge base

Vai su **Governance → Lesson Learned → Knowledge base**. Puoi cercare per:

- **Parola chiave**: ricerca testuale su titolo e descrizione
- **Framework / controllo**: filtra per controlli impattati
- **Tipo di evento**: incidente, finding, rischio, miglioramento volontario
- **Plant**: solo lesson learned del tuo plant, o di tutti i plant (se hai accesso multi-plant)
- **Periodo**: data di approvazione

Vengono mostrate solo le lesson learned approvate. Le bozze sono visibili solo all'owner e ai revisori.

---

## 11. Revisione Direzione (M13)

[Schermata: revisione direzione]

### Come creare una revisione

1. Vai su **Governance → Revisione Direzione → Nuova**
2. Compila:
   - **Anno e numero**: es. "2026 — Rev. 1/2026"
   - **Data pianificata**
   - **Partecipanti**: seleziona i ruoli coinvolti (Plant Manager, CISO, Risk Manager, CO)
3. Il sistema aggiunge automaticamente i punti obbligatori all'ordine del giorno (vedi sotto)
4. Puoi aggiungere punti extra tramite **Aggiungi punto OdG**
5. Clicca **Salva bozza**

### Punti all'ordine del giorno obbligatori (ISO 27001 cl.9.3)

La norma ISO 27001 clausola 9.3 impone che la revisione di direzione includa obbligatoriamente una serie di punti. Il sistema li inserisce automaticamente nella bozza:

- Stato delle azioni delle revisioni precedenti
- Cambiamenti nel contesto interno ed esterno rilevanti per il SGSI
- Feedback sulle prestazioni del SGSI (NC, audit, monitoraggio, misurazioni)
- Feedback delle parti interessate
- Risultati della valutazione dei rischi e stato del piano di trattamento
- Opportunita' di miglioramento continuo

Non e' possibile chiudere una revisione se uno di questi punti non ha almeno un commento o una decisione registrata.

### Come registrare le decisioni

Per ogni punto all'ordine del giorno:

1. Clicca sul punto per espanderlo
2. Inserisci il **riepilogo della discussione**
3. Clicca **Aggiungi decisione** per registrare le azioni approvate dalla direzione
4. Per ogni decisione specifica: responsabile, azione da intraprendere, scadenza

Le decisioni con responsabile e scadenza vengono automaticamente trasformate in task in M08 e, se strutturali, in cicli PDCA in M11.

### Chiusura e approvazione

1. Dopo aver completato tutti i punti obbligatori clicca **Invia per approvazione**
2. Il Plant Manager riceve un task di approvazione
3. Una volta approvata, la revisione diventa immutabile
4. Viene generato automaticamente il verbale in PDF firmato con hash e timestamp, disponibile nella sezione **Documenti generati** della revisione

---

## 12. Audit Preparation (M17)

[Schermata: audit preparation — lista programmi]

### Programma Annuale

#### Come creare il programma con il wizard (4 step)

1. Vai su **Audit → Audit Preparation → Nuovo programma**
2. Si apre il wizard in 4 step:

**Step 1 — Dati base**
- Anno del programma (es. 2026)
- Plant di riferimento
- Framework da auditare (ISO 27001, TISAX L2, TISAX L3, NIS2 — seleziona uno o piu')
- Nome del programma (es. "Programma Audit ISO 27001 — Stabilimento Nord 2026")

**Step 2 — Parametri copertura**
Scegli il livello di copertura dell'audit:
- **Campione (25%)**: audit spot su un quarto dei controlli. Adatto per verifiche intermedie o quando le risorse sono limitate
- **Esteso (50%)**: copertura della meta' dei controlli. Bilanciamento tra profondita' e sostenibilita'
- **Full (100%)**: audit completo di tutti i controlli del framework. Richiesto per le certificazioni formali

**Step 3 — Revisione piano suggerito**
Il sistema analizza lo stato attuale dei controlli e genera un piano suggerito che:
- Concentra Q1 e Q3 sui **domini con piu' gap** (i piu' critici vengono auditati prima)
- Distribuisce i controlli rimanenti nei trimestri Q2 e Q4
- Suggerisce gli auditor in base ai ruoli disponibili nel plant

Puoi modificare manualmente: le date di ogni trimestre, l'auditor assegnato a ogni sessione, la lista dei controlli inclusi in ogni trimestre.

**Step 4 — Approvazione**
- Rivedi il riepilogo del programma
- Clicca **Approva programma**
- Il programma diventa attivo e visibile a tutti i ruoli coinvolti

#### Come interpretare il piano suggerito

Il sistema prioritizza i domini con piu' gap nei trimestri iniziali (Q1 e Q3) per dare tempo sufficiente alla risoluzione prima di eventuali audit di certificazione. I domini con buona copertura vengono assegnati ai trimestri Q2 e Q4. Controlla che la distribuzione sia sostenibile in termini di carico di lavoro per gli auditor.

#### Come modificare date e auditor per trimestre

Dal dettaglio del programma approvato:
1. Clicca sull'icona di modifica accanto al trimestre da aggiornare
2. Modifica la data di inizio/fine e l'auditor assegnato
3. Salva — la modifica viene registrata nel log del programma

#### Come approvare il programma

Al completamento dello Step 4 del wizard il programma passa automaticamente in stato "Approvato". Il Compliance Officer riceve una notifica. Il programma e' ora visibile agli auditor assegnati.

---

### Esecuzione Audit

[Schermata: dettaglio trimestre audit]

#### Come avviare un audit da un trimestre

1. Dal programma approvato, vai al trimestre di interesse
2. Clicca **Avvia audit** — il trimestre passa da "Pianificato" a "In corso"
3. Si apre la checklist dei controlli da verificare per quel trimestre

#### Copertura campione vs full — differenze pratiche

- **Campione**: vedi solo il sottoinsieme di controlli selezionati dal sistema (25% o 50% del totale). Non puoi aggiungere controlli non inclusi nel campione
- **Full**: vedi tutti i controlli del framework. Devi compilare l'evidenza per ognuno prima di poter chiudere l'audit

In entrambi i casi la struttura della checklist e' identica — la differenza e' solo nel numero di controlli da verificare.

#### Come compilare la checklist controlli

Per ogni controllo nella checklist:
1. Clicca sul controllo per espandere il dettaglio
2. Verifica lo stato dichiarato e l'evidenza collegata
3. Scegli il **giudizio dell'auditor**: Confermato / Non Conforme / Osservazione / Opportunita'
4. Se il giudizio e' diverso da "Confermato" clicca **Aggiungi finding** (vedi sotto)
5. Aggiungi eventuali note dell'auditor nel campo apposito
6. Clicca **Salva giudizio**

#### Come aggiungere un finding

1. Dalla scheda del controllo clicca **Aggiungi finding**
2. Compila:
   - **Titolo del finding**
   - **Descrizione dettagliata**: cosa manca o non e' conforme
   - **Tipo di finding** (vedi tabella sotto)
   - **Controllo di riferimento**
   - **Evidenza a supporto**: opzionale in fase di apertura, obbligatoria per Major NC

#### Tipi di finding e scadenze risposta

| Tipo | Significato | Scadenza risposta |
|------|-------------|------------------|
| **Major NC** (Non Conformita' Maggiore) | Requisito non soddisfatto con impatto significativo sulla conformita' o sulla sicurezza | 30 giorni |
| **Minor NC** (Non Conformita' Minore) | Requisito parzialmente non soddisfatto, impatto limitato | 90 giorni |
| **Observation** | Potenziale debolezza che non e' ancora una non conformita'. Da monitorare | 180 giorni |
| **Opportunity** | Suggerimento di miglioramento senza impatto sulla conformita'. Nessuna scadenza obbligatoria | — |

Le scadenze di risposta sono calcolate automaticamente dalla data di apertura del finding in base a queste policy. Per Major NC viene creato automaticamente anche un ciclo PDCA.

#### Come chiudere un finding

1. Dalla scheda del finding, dopo aver adottato le azioni correttive, clicca **Proponi chiusura**
2. Carica l'**evidenza di chiusura** (obbligatoria per Major NC e Minor NC)
3. Inserisci il **commento di chiusura**: descrivi le azioni intraprese
4. Il finding passa in stato "In verifica"
5. L'auditor responsabile verifica l'evidenza e clicca **Conferma chiusura** o **Riapri finding** con commento

#### Come scaricare la relazione audit

Dall'audit in corso o chiuso:
1. Clicca il pulsante **Report** (icona PDF) in alto a destra nella pagina dell'audit
2. Scegli la lingua del report
3. Il sistema genera un PDF con: riepilogo copertura, lista finding per tipo, stato di chiusura, trend rispetto all'audit precedente
4. Il PDF e' disponibile immediatamente per il download

---

### Annullare un audit

[Schermata: pulsante annulla audit]

#### Quando usare "Annulla" vs eliminazione

- Usa **Annulla** quando un audit pianificato non verra' eseguito ma vuoi mantenere traccia della pianificazione originale (es. cambio data, cambio scope, emergenza aziendale)
- L'**eliminazione** non e' disponibile per gli audit in stato "In corso" o "Chiuso" — usa sempre "Annulla" per gli audit avviati

#### Come annullare

1. Dalla lista degli audit, clicca il pulsante **Annulla** (icona X) sulla riga dell'audit
2. Si apre un dialogo che richiede la **motivazione dell'annullamento** (obbligatoria, minimo 10 caratteri)
3. Inserisci la motivazione (es. "Rinviato al Q3 per disponibilita' auditor")
4. Clicca **Conferma annullamento**

#### Cosa succede ai finding aperti

Quando annulli un audit che ha gia' finding aperti:
- I finding vengono **chiusi automaticamente** con stato "Annullato" e la motivazione dell'annullamento
- I PDCA collegati ai finding restano aperti e devono essere gestiti manualmente
- Il programma annuale non viene modificato — il trimestre viene marcato come "Annullato" con traccia della motivazione

L'audit annullato non viene mai eliminato fisicamente — rimane nell'archivio con stato "Annullato" per garantire la tracciabilita'.

---

## 13. Fornitori (M14)

[Schermata: lista fornitori]

### Come registrare un fornitore

1. Vai su **Governance → Fornitori → Nuovo fornitore**
2. Compila:
   - **Ragione sociale** e **Partita IVA**
   - **Categoria**: IT, OT, Servizi Professionali, Logistica, altro
   - **Criticita'**: quanto e' critico per la continuita' operativa (1–5)
   - **Referente interno**: seleziona il ruolo responsabile della gestione del fornitore
   - **Referente fornitore**: nome e email del contatto presso il fornitore
   - **Trattamento dati**: flag se il fornitore tratta dati personali (comporta obblighi GDPR aggiuntivi)
3. Clicca **Salva**

### Assessment: pianificato → in corso → completato → approvato/rifiutato

Ogni fornitore critico deve essere periodicamente valutato tramite assessment. Il flusso e':

1. **Pianificato**: l'assessment viene creato con data target. Il referente interno riceve un task
2. **In corso**: l'assessment viene avviato. Il fornitore riceve (via email o accesso temporaneo) il questionario da compilare
3. **Completato**: il fornitore ha risposto a tutte le domande. Il referente interno riceve il questionario per la revisione
4. **Approvato** o **Rifiutato**: il Compliance Officer o il Risk Manager esprime il giudizio finale (vedi sotto)

### Score governance, security, BCP

Il questionario di assessment valuta il fornitore su 3 dimensioni:

| Dimensione | Cosa valuta |
|-----------|-------------|
| **Governance** | Struttura organizzativa per la sicurezza, politiche interne, responsabilita' definite, audit interni |
| **Security** | Controlli tecnici implementati, gestione vulnerabilita', incident response, certificazioni (ISO 27001, TISAX) |
| **BCP** | Piani di continuita' operativa, RTO/RPO dichiarati, test di continuita' eseguiti, ridondanze infrastrutturali |

Ogni dimensione produce uno score 0-100. Lo score complessivo e' la media pesata delle tre dimensioni.

### Approvazione e rifiuto con note obbligatorie

**Approvazione:**
1. Dalla scheda dell'assessment completato clicca **Approva fornitore**
2. Inserisci le **note di approvazione** (obbligatorie — es. "Fornitore certificato ISO 27001, punteggio adeguato. Prossima revisione tra 12 mesi")
3. Imposta la **data di scadenza dell'approvazione** (tipicamente 12 mesi)
4. Clicca **Conferma approvazione**

**Rifiuto:**
1. Dalla scheda dell'assessment completato clicca **Rifiuta fornitore**
2. Inserisci le **note di rifiuto** (obbligatorie — deve essere una motivazione dettagliata che giustifichi la decisione)
3. Clicca **Conferma rifiuto**

Il rifiuto genera un task al referente interno per gestire la transizione (sostituzione fornitore o piano di remediation).

---

## 14. Formazione (M15)

[Schermata: piano formativo personale]

### Come vedere i propri corsi obbligatori

1. Vai su **Governance → Formazione → Il mio piano**
2. Trovi l'elenco dei corsi obbligatori per il tuo ruolo e plant, con:
   - Nome del corso
   - Stato: Da completare / In corso / Completato / Scaduto
   - Data di scadenza (o data di completamento se gia' fatto)
   - Tipo: online (KnowBe4), presenza, documentale

### Completion e scadenze

- Clicca **Avvia corso** sui corsi online per aprire direttamente il modulo su KnowBe4
- I completamenti vengono sincronizzati automaticamente ogni notte — se hai completato un corso su KnowBe4 e non appare ancora come completato nella GRC Platform, aspetta il giorno successivo o contatta il Compliance Officer
- Un corso scaduto (completato ma da rifare periodicamente) appare con badge rosso e genera un task di rinnovo

### Gap analysis competenze

Vai su **Governance → Formazione → Gap analysis**. La pagina mostra:

- I requisiti di competenza previsti per ogni ruolo e plant
- Le competenze effettivamente certificate (corsi completati, attestati caricati)
- I gap evidenziati: competenze richieste ma non ancora coperte da alcun corso completato

Il Compliance Officer puo' usare questa vista per pianificare le sessioni formative e colmare i gap prioritari.

### Sincronizzazione KnowBe4 (solo admin)

Vai su **Impostazioni → Integrazioni → KnowBe4**:

1. Configura la API key KnowBe4
2. Clicca **Sincronizza ora** per forzare la sincronizzazione immediata dei completamenti
3. Verifica il log dell'ultima sincronizzazione per individuare eventuali errori

La sincronizzazione automatica avviene ogni notte alle 02:00.

---

## 15. Business Continuity (M16)

[Schermata: lista piani BCP]

### Come creare un piano BCP

1. Vai su **Governance → BCP → Nuovo piano**
2. Compila:
   - **Nome del piano** (es. "Piano BCP — Linea produzione B — Stabilimento Sud")
   - **Scope**: processi critici coperti dal piano (seleziona dalla BIA)
   - **Owner del piano**: responsabile della manutenzione
   - **RTO obiettivo** e **RPO obiettivo**: i valori che il piano deve garantire
3. Clicca **Salva bozza**

### Collegamento con RTO/RPO della BIA

Nella sezione **Processi coperti** del piano BCP, per ogni processo selezionato viene mostrato il confronto tra:

- **RTO richiesto dalla BIA**: il massimo tollerabile dichiarato nel processo critico
- **RTO garantito dal BCP**: quello che il piano riesce effettivamente a garantire

Se il BCP garantisce un RTO superiore a quello richiesto dalla BIA, appare un avviso arancione che richiede revisione. Il sistema non blocca il salvataggio ma richiede una giustificazione esplicita.

### Tipi di test

Il piano deve essere testato periodicamente. I tipi di test disponibili sono:

| Tipo | Descrizione |
|------|-------------|
| **Tabletop** | Simulazione su carta/discussione. Partecipanti in sala riunioni, nessun sistema reale coinvolto |
| **Simulation** | Simulazione parziale con alcuni sistemi reali in modalita' test, senza interruzione della produzione |
| **Full** | Test completo con attivazione del piano su sistemi reali, senza impatto sulla produzione normale |
| **Drill** | Esercitazione non annunciata per testare i tempi di risposta reali del team |

Per registrare un test: dalla scheda del piano clicca **Nuovo test**, seleziona il tipo, la data, i partecipanti e l'esito.

### Cosa succede se il test fallisce (PDCA automatico)

Se il test viene registrato con esito **Fallito** o **Parzialmente superato**:

1. Viene creato automaticamente un ciclo PDCA con fase di partenza PLAN
2. Il PDCA viene assegnato all'owner del piano BCP
3. L'owner deve compilare il piano d'azione entro 30 giorni
4. Il piano BCP resta in stato "Da aggiornare" finche' il PDCA non viene chiuso positivamente

### Scadenza piani e alert

Ogni piano BCP ha una data di revisione obbligatoria (tipicamente annuale). Quando la data si avvicina:

- **30 giorni prima**: notifica email all'owner del piano
- **Alla scadenza**: il piano passa in stato "Scaduto" con badge rosso. Viene creato automaticamente un task di revisione
- Se il piano scaduto copre processi con MTPD < 48 ore, viene inviata una notifica di escalation al Plant Manager

---

## 16. Activity Schedule (Scadenzario)

[Schermata: scadenzario con vista calendario]

### Come leggere il calendario scadenze

Vai su **Operazioni → Scadenzario**. La pagina mostra tutte le scadenze nel periodo selezionato (default: prossimi 30 giorni), ordinate per data. Per ogni scadenza vedi:

- **Tipo** di scadenza (documento, evidenza, task, assessment, piano BCP, corso formativo, ecc.)
- **Nome** dell'elemento
- **Data** di scadenza
- **Owner** responsabile
- **Stato** con badge colorato (vedi sotto)

Puoi passare tra la vista lista e la vista calendario cliccando le icone in alto a destra.

### Filtri per tipo e periodo

Nella barra filtri sopra la lista puoi filtrare per:

- **Tipo**: seleziona uno o piu' tipi di scadenza (documenti, evidenze, task, assessment, BCP, formazione)
- **Periodo**: questa settimana / questo mese / prossimi 30 giorni / prossimi 90 giorni / range personalizzato
- **Owner**: filtra per il responsabile della scadenza
- **Plant**: filtra per stabilimento (se hai accesso multi-plant)

### Colori dei badge

| Colore | Significato |
|--------|-------------|
| **Verde** | Valido — nessuna azione richiesta, scadenza lontana |
| **Giallo** | In scadenza — mancano meno di 30 giorni. Controlla e pianifica l'azione |
| **Rosso** | Scaduto — la data e' gia' passata. Azione urgente richiesta |

### Come navigare direttamente all'elemento dalla scadenza

Clicca sul nome di qualsiasi scadenza nella lista per aprire direttamente la scheda dell'elemento interessato (es. cliccando su un'evidenza in scadenza apri la scheda dell'evidenza). Non e' necessario navigare manualmente attraverso i menu.

---

## 17. Documenti Obbligatori

[Schermata: pagina documenti obbligatori]

### Come collegare un documento a un requisito normativo

I documenti obbligatori sono quelli richiesti esplicitamente da un framework normativo (es. ISO 27001 richiede una "Politica per la sicurezza delle informazioni"). Per collegare un documento esistente a un requisito:

1. Vai su **Compliance → Documenti obbligatori**
2. Trova il requisito normativo nella lista
3. Clicca **Collega documento** accanto al requisito
4. Cerca e seleziona il documento appropriato dalla libreria documenti (M07)
5. Salva

Se il documento non esiste ancora clicca **Crea documento** per avviare il workflow di creazione in M07.

### Semaforo di stato

Per ogni requisito normativo nella lista, il semaforo mostra lo stato del documento collegato:

| Colore semaforo | Significato |
|-----------------|-------------|
| **Verde** | Documento presente, approvato e valido (non scaduto) |
| **Giallo** | Documento presente e approvato ma in scadenza entro 30 giorni — pianifica la revisione |
| **Rosso** | Documento presente ma scaduto — aggiornamento urgente richiesto |
| **Grigio** | Documento mancante — nessun documento collegato a questo requisito |

I requisiti con semaforo grigio impattano negativamente il KPI di compliance del framework.

### Come aggiungere un documento mancante

Quando il semaforo e' grigio (documento mancante):

1. Clicca sul requisito
2. Clicca **Crea e collega documento** per avviare il wizard di creazione
3. Il sistema precompila automaticamente il titolo suggerito, il framework di riferimento e i campi normativi del documento
4. Completa i campi mancanti (owner, revisore, approvatore) e carica il file
5. Il documento parte in stato Bozza e segue il normale workflow di approvazione (M07)
6. Una volta approvato, il semaforo passa automaticamente a verde

---

## 18. Notifiche Email

### Quando arrivano le notifiche

La piattaforma invia notifiche email automatiche in base agli eventi. Le principali:

| Evento | Destinatari |
|--------|-------------|
| Task assegnato | Owner del ruolo destinatario |
| Task in scadenza (7 giorni) | Owner del ruolo + responsabile |
| Task scaduto | Owner + responsabile + Compliance Officer (dopo 14 giorni) |
| Finding di audit aperto | Responsabile area auditata |
| Finding in scadenza (30/90/180 giorni) | Owner del finding |
| Audit imminente (7 giorni) | Auditor + Compliance Officer |
| Incidente NIS2 — timer T+24h | CISO + Compliance Officer |
| Incidente NIS2 — timer T+72h | CISO + Compliance Officer + Plant Manager |
| Rischio con score > 14 | Risk Manager + Plant Manager |
| Documento in scadenza (30 giorni) | Owner del documento |
| Evidenza scaduta | Owner del controllo collegato |
| Ruolo vacante obbligatorio | Compliance Officer + Plant Manager |
| Assessment fornitore in scadenza (30 giorni) | Referente interno |

Alcune notifiche sono obbligatorie e non disattivabili (es. timer NIS2, escalation task critici, rischi rossi).

### Come cambiano in base al profilo assegnato al ruolo

Le notifiche inviate per un ruolo dipendono dal **profilo notifica** assegnato a quel ruolo (configurato in Impostazioni). Un ruolo con profilo "Essenziale" riceve solo le notifiche obbligatorie e le scadenze critiche. Un ruolo con profilo "Completo" riceve anche i digest periodici e le notifiche sui moduli di riferimento.

### Come configurare le preferenze (solo admin)

Vai su **Impostazioni → Profili notifica**:

1. Seleziona il profilo da modificare o clicca **Nuovo profilo**
2. Configura per ogni tipo di evento: attivo / inattivo, frequenza (immediata / digest giornaliero / digest settimanale)
3. Assegna il profilo ai ruoli che devono usarlo
4. Salva

La configurazione si applica immediatamente. I cambiamenti non sono retroattivi sulle notifiche gia' inviate.

---

## 19. Governance (M00)

[Schermata: organigramma ruoli normativi]

### Come assegnare un ruolo normativo

I ruoli normativi sono posizioni richieste dai framework (es. CISO, DPO, Risk Owner, Asset Owner). Per assegnare un titolare:

1. Vai su **Governance → Organigramma**
2. Trova il ruolo da assegnare (eventualmente usa il filtro per framework o plant)
3. Clicca **Assegna titolare**
4. Seleziona l'utente dall'elenco
5. Imposta:
   - **Data inizio**: da quando ha effetto l'assegnazione
   - **Data scadenza** (facoltativa): utile per incarichi temporanei o rotazioni programmate
6. Clicca **Conferma assegnazione**

L'assegnazione viene registrata nell'audit trail. L'utente riceve una notifica email con le responsabilita' del ruolo.

### Come sostituire un titolare (successione)

Se un titolare va in pensione, cambia funzione o lascia l'azienda, usa il meccanismo di successione:

1. Dalla scheda del ruolo clicca **Gestisci successione**
2. Seleziona il nuovo titolare
3. Imposta la **data di transizione**
4. Il sistema gestisce automaticamente la sovrapposizione: fino alla data di transizione il vecchio titolare rimane attivo, dal giorno successivo subentra il nuovo
5. Clicca **Conferma successione**

Il vecchio titolare riceve una notifica di fine incarico. Il nuovo titolare riceve una notifica di inizio incarico con l'elenco delle responsabilita'.

### Come terminare un ruolo

Se una posizione non e' piu' richiesta (es. cambio di scope normativo):

1. Dalla scheda del ruolo clicca **Termina ruolo**
2. Inserisci la **motivazione** (obbligatoria — es. "Ruolo eliminato dopo revisione scope TISAX 2026")
3. Imposta la **data di termine**
4. Se ci sono task aperti assegnati a questo ruolo, il sistema ti chiede come gestirli (riassegna ad altro ruolo o lascia aperti)
5. Clicca **Conferma**

### Alert ruoli in scadenza e ruoli vacanti obbligatori

**Ruoli in scadenza**: se un'assegnazione ha una data di scadenza, 30 giorni prima il sistema invia una notifica al Compliance Officer e al Plant Manager per pianificare il rinnovo o la successione.

**Ruoli vacanti obbligatori**: alcuni ruoli sono marcati come obbligatori nel framework (es. CISO per ISO 27001). Se un ruolo obbligatorio non ha un titolare attivo:
- Appare un banner rosso nella dashboard
- Il KPI di compliance viene penalizzato
- Viene generato un task urgente di assegnazione

---

## 20. Impostazioni (solo Admin)

[Schermata: pagina impostazioni admin]

Questa sezione e' accessibile solo agli utenti con ruolo Amministratore di sistema o Super Admin.

### Configurazione email SMTP

1. Vai su **Impostazioni → Email → Configurazione SMTP**
2. Compila:
   - **Host SMTP** (es. smtp.azienda.com)
   - **Porta** (tipicamente 587 per STARTTLS o 465 per SSL)
   - **Utente** e **Password** — la password viene cifrata con AES-256 (FERNET) prima di essere salvata
   - **Mittente predefinito** (es. noreply@grc.azienda.com)
   - **TLS/SSL**: seleziona il tipo di cifratura
3. Clicca **Salva configurazione**

### Test connessione email

Dopo aver configurato l'SMTP:

1. Nella stessa pagina clicca **Invia email di test**
2. Inserisci un indirizzo email destinatario per il test
3. Clicca **Invia**
4. Controlla la ricezione. Se l'email non arriva entro 2 minuti clicca **Visualizza log** per vedere l'eventuale errore SMTP

### Profili notifica per ruolo

Vai su **Impostazioni → Notifiche → Profili**:

1. I profili predefiniti sono: Essenziale, Standard, Completo, Silenzioso
2. Per creare un profilo personalizzato clicca **Nuovo profilo**
3. Per ogni tipo di notifica imposta: attivo/inattivo e frequenza di invio
4. Assegna il profilo ai ruoli tramite **Impostazioni → Ruoli → seleziona ruolo → Profilo notifica**

### Policy scadenze (23 tipi configurabili)

Vai su **Impostazioni → Policy → Scadenze**. Puoi configurare i tempi di preavviso e le scadenze predefinite per 23 tipi di elementi, tra cui:

- Evidenze per tipo (log: 30gg, scan: 90gg, certificati: 365gg)
- Documenti per tipo (policy: 365gg, procedura: 730gg)
- Finding per severita' (Major NC: 30gg, Minor NC: 90gg, Observation: 180gg)
- Assessment fornitori (12 mesi default)
- Piani BCP (12 mesi default)
- Revisione rischi (90gg per rischi rossi, 180gg per rischi gialli)

Modificando questi valori si aggiornano i calcoli su tutti gli elementi futuri. Gli elementi esistenti mantengono le scadenze calcolate al momento della creazione.

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
- Validare la BIA e i valori MTPD/RTO/RPO (M05)
- Avviare e monitorare i cicli PDCA (M11)
- Ricevere alert su rischi con score > 14

### Plant Manager

Hai accesso al tuo plant. Sei responsabile di:

- Approvare i documenti di livello direzione (M07)
- Ricevere escalation su task critici scaduti
- Validare le decisioni di risk treatment (M06)
- Partecipare e approvare la revisione di direzione (M13)

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

## AI Engine — suggerimenti IA (M20)

> Il modulo AI e' abilitato solo se il tuo amministratore ha attivato questa funzione per il tuo plant.

### Come funziona

Quando il modulo AI e' attivo, vedrai un riquadro **Suggerimento IA** in alcuni moduli — incidenti, asset, documenti, task. Il sistema analizza il contesto e propone:

- Una **classificazione suggerita** (es. severita' incidente, criticita' asset)
- Una **bozza di testo** (es. notifica ACN, policy, RCA)
- Un **alert proattivo** (es. task con alto rischio di slittamento)

### Cosa devi fare

Il suggerimento IA non ha effetto fino a quando non lo **confermi esplicitamente**. Puoi:

- **Accettare** il suggerimento cosi' com'e' — clicca **Usa questo suggerimento**
- **Modificare** il testo e poi cliccare **Usa versione modificata** — la tua versione sovrascrive quella dell'IA
- **Ignorare** il suggerimento e procedere manualmente — il riquadro si chiude senza effetti

> Ogni interazione (suggerimento ricevuto, testo finale adottato) viene registrata nell'audit trail per garantire la tracciabilita' delle decisioni. L'IA non prende mai decisioni autonomamente.

---

## Reporting ed export (M18)

### Dashboard reporting

Vai su **Audit → Reporting**. Trovi tre livelli di dashboard:

- **Operativa**: stato task, controlli per framework e plant, scadenze
- **Risk**: heat map aggregata, top 10 rischi aperti
- **Executive**: compliance %, trend maturita' PDCA, readiness audit

### Generare un report PDF

1. Seleziona il tipo di report (gap TISAX, compliance NIS2, SOA ISO 27001, BIA executive)
2. Scegli il plant e il periodo
3. Seleziona la lingua del report
4. Clicca **Genera** — il PDF viene firmato con timestamp e hash
5. Il report e' disponibile per il download nella sezione **Report generati**

Tutti i report generati sono registrati nell'audit trail.

---

## Appendice: Domande frequenti

**Non trovo un controllo che dovrebbe essere nel mio framework.**
Verifica di aver selezionato il plant corretto nel selettore in alto. Se il framework e' attivo per quel plant ma il controllo non appare, contatta il Compliance Officer — potrebbe non essere stato generato durante l'attivazione del framework.

**Ho caricato un'evidenza ma il controllo mostra ancora "gap".**
Verifica che l'evidenza sia collegata al controllo corretto (scheda evidenza → sezione "Controlli coperti") e che la data di scadenza non sia gia' passata.

**Il timer NIS2 e' partito ma l'incidente non e' davvero un incidente NIS2.**
Il CISO ha 30 minuti per escludere l'obbligo di notifica. Se sei il CISO, apri la scheda incidente e clicca **Escludi obbligo NIS2** inserendo la motivazione. I timer si fermano e la decisione viene registrata nell'audit trail.

**Ho completato un task ma continua ad apparire come aperto.**
Alcuni task si chiudono automaticamente quando l'azione nel modulo origine e' completata. Se il task e' manuale, devi chiuderlo esplicitamente dalla scheda del task → **Segna come completato**.

**Un documento che avevo approvato risulta ora "in revisione".**
E' stato attivato un trigger di revisione straordinaria — probabilmente collegato a un incidente, un finding di audit o un cambio normativo. Controlla le note nella scheda del documento per capire il motivo.

**Non riesco ad impostare un controllo come N/A.**
Per i controlli TISAX L3 lo stato N/A richiede la firma di almeno due ruoli (doppio lock). Se sei il primo ad approvare, il controllo rimane in attesa della seconda firma. Se sei l'unico proprietario, contatta il CISO per la co-firma.

**Il suggerimento IA non appare piu'.**
Il modulo AI potrebbe essere stato disabilitato dall'amministratore per il tuo plant, oppure la funzione specifica non e' attiva. Contatta il Compliance Officer o il System Administrator.

**Ho annullato un audit per errore. Posso ripristinarlo?**
No, l'annullamento e' irreversibile. Puoi pero' creare un nuovo audit per lo stesso trimestre e ricreare i finding eventualmente persi. Contatta il Compliance Officer che puo' visualizzare i finding annullati nell'archivio per recuperare le informazioni.

**Lo score del mio rischio e' cambiato senza che io abbia fatto nulla.**
Lo score residuo viene ricalcolato automaticamente quando cambia lo stato dei controlli collegati. Se un'evidenza e' scaduta, il controllo torna a "parziale" e questo puo' aumentare il rischio residuo. Controlla i controlli collegati al rischio e aggiorna le evidenze.

**Non ricevo le notifiche email.**
Verifica innanzitutto la cartella spam. Se le email non arrivano affatto, contatta l'amministratore di sistema per verificare la configurazione SMTP e il profilo notifica assegnato al tuo ruolo.

**Come posso vedere la cronologia delle modifiche su un asset o un documento?**
Ogni scheda ha una sezione **Audit trail** o **Storico modifiche** in basso. Clicca su di essa per vedere tutte le azioni registrate con data, utente e dettaglio della modifica.

**Il programma di audit mostra lo stato "Da aggiornare". Cosa devo fare?**
Lo stato "Da aggiornare" indica che il programma e' stato creato ma alcune informazioni (es. auditor non assegnato a un trimestre, date mancanti) richiedono completamento prima che il programma possa essere approvato. Apri il programma e cerca i campi evidenziati in giallo.
