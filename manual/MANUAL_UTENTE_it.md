# Manuale Utente — govrico

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
- [Centro Operativo (M21)](#centro-operativo-m21)
- [OSINT Monitor](#osint-monitor)
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

La lingua selezionata si applica a tutta l'interfaccia. I report e gli export generati utilizzano la lingua attiva al momento della generazione.

### Menu laterale: sezioni principali e cosa contengono

[Schermata: sidebar con menu espanso]

Il menu laterale a sinistra mostra solo le sezioni accessibili in base al tuo ruolo. Le voci principali sono:

| Gruppo | Voci |
|--------|------|
| **Principale** | Dashboard · Centro Operativo (M21)¹ · Reporting (M18) · KPI Operativi · Task (M08) · Checklist |
| **Compliance** | Controlli (M03) · Gap Analysis · Documenti (M07) · Audit Prep (M17) |
| **Rischio e continuità** | BIA (M05) · Risk (M06) · Asset IT/OT (M04) · BCP (M16) |
| **Operazioni** | Incidenti (M09) · Lessons (M12) · Fornitori (M14) · Formazione (M15) · PDCA (M11) |
| **Pianificazione** | Activity Schedule · Documenti Obbl. · Policy Scadenze² · Template Checklist³ |
| **Organizzazione e revisione** | Governance (M00) · Obiettivi di sicurezza · Revisione Dir. (M13)⁴ · Siti (M01)² · Utenti (M02)⁵ · Competenze⁶ · Audit Trail (M10)⁷ · Autenticazione MFA |
| **Sicurezza**⁸ | OSINT Monitor |
| **Impostazioni**⁵ | Config. Email · Regole Notifiche · Govrico AI · Backup & Restore |

Voci riservate ad alcuni ruoli:

1. Super Admin, Compliance Officer, Risk Manager, Internal Auditor, Plant Manager
2. Super Admin, Compliance Officer
3. Super Admin, Compliance Officer, CISO, Risk Manager
4. Super Admin, Compliance Officer, Risk Manager
5. Super Admin
6. Super Admin, Compliance Officer, CISO
7. Super Admin, Internal Auditor, External Auditor
8. Super Admin, CISO, Compliance Officer

Il pulsante **«** in alto riduce il menu alle sole icone (il nome della voce compare passandoci sopra con il mouse) e **»** lo riapre. La scelta viene ricordata tra una sessione e l'altra.

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
| **N/A** | Il controllo non si applica al contesto del tuo plant. Richiede una giustificazione scritta di almeno 20 caratteri. La giustificazione è salvata e visibile ogni volta che si riapre il controllo. Nel VDA ISA TISAX viene riportata nella colonna "Note / Justification" e il maturity level è impostato a 0. Per TISAX L3 richiede la firma di due ruoli e scade dopo 12 mesi |

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

### Come compilare l'Implementation description TISAX (intervista guidata)

Il VDA ISA si compila in inglese: per ogni controllo TISAX l'auditor legge, accanto alla maturità dichiarata, **come** il requisito è implementato. Nel tab **Valutazione** del controllo c'è il riquadro «Implementation description (VDA ISA)»: si può scrivere direttamente il testo in inglese oppure usare l'intervista guidata, che simula il confronto con un auditor TISAX.

1. Clicca **Compila con l'intervista guidata (IA)**
2. L'auditor ti fa **2–4 domande per tema** nella tua lingua (per esempio, per la politica di sicurezza: i documenti, la loro approvazione e revisione, la comunicazione a dipendenti e partner). Per ogni domanda vedi **cosa vuole capire l'auditor**, **cosa citare** e, a richiesta, **un esempio** con segnaposto tra parentesi quadre: adattalo alla tua realtà, non copiarlo. «Requisiti VDA di questa domanda» mostra i requisiti originali in inglese (per i controlli L3 anche quelli del controllo L2 esteso)
3. Rispondi in modo concreto: quali documenti, chi è responsabile, come avviene, ogni quanto. Scrivi «no» se qualcosa non è ancora in atto. Nomi di persone e dati personali non servono
4. **Verifica con l'auditor** (al massimo **2 giri**): l'auditor indica per ogni requisito se è coperto, parziale o non coperto, la **maturità** che le risposte sostengono (con un avviso se è più bassa di quella dichiarata), le **evidenze** che chiederà in sede (segnalando quelle già collegate al controllo) e fino a 3 **domande di approfondimento** su ciò che manca. Rispondi agli approfondimenti e, se serve, fai il secondo giro. Finiti i giri si può ricominciare la verifica: le risposte alle domande restano
5. **Genera bozza in inglese**: l'IA scrive la descrizione dall'intera conversazione, per tema e senza ripetere i fatti, usando solo quello che hai scritto. I requisiti obbligatori ancora scoperti all'ultima verifica sono segnati `[TO BE COMPLETED]`. Accanto c'è la traduzione nella tua lingua per la verifica
6. **Usa questa bozza** copia il testo nel campo descrizione: rileggilo, correggilo se serve e premi **Salva descrizione**

Le risposte si salvano con **Salva risposte** (anche verifica e bozza le salvano) e restano sul controllo per la rivalutazione dell'anno successivo. L'intervista resta nella lingua in cui è stata iniziata. La bozza non viene mai salvata da sola: resta registrato nell'audit trail chi ha salvato la descrizione e se proveniva dall'IA. Se l'IA non è configurata l'intervista non è disponibile e il riquadro mostra i requisiti originali per scrivere la descrizione a mano. Il Centro Operativo segnala i controlli TISAX con maturità ≥ 3 senza descrizione.

### Come scaricare SOA ISO 27001, VDA ISA TISAX, NIS2 Matrix

[Schermata: pagina export compliance]

1. Vai su **Compliance → Libreria controlli**
2. Clicca il pulsante **Esporta** (icona download) in alto a destra nella pagina
3. Seleziona il tipo di export:
   - **SOA ISO 27001** — Statement of Applicability con tutti i controlli Annex A e il relativo stato
   - **VDA ISA TISAX** — Tabella VDA Information Security Assessment, in formato orizzontale (A4 landscape): per ogni controllo maturità, stato, owner, **Implementation description**, **Reference documentation** (documenti ed evidenze collegati) e Note / Justification. I controlli con maturità ≥ 3 senza descrizione sono segnati "Missing" e contati nell'intestazione. La descrizione si compila nel tab **Valutazione** del controllo, riquadro «Implementation description (VDA ISA)»
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

### Propagazione stato tra framework (e tra plant)

Il pulsante **Propaga** è disponibile nella lista controlli, accanto allo stato, per i controlli in stato **Compliant** o **N/A** che hanno mapping verso altri framework.

**Come funziona:**

| Tipo di mapping | Direzione | Esempio |
|-----------------|-----------|---------|
| `Equivalente` | Bidirezionale | ISO A.8.1 ≡ TISAX ISA-1.1 → propaga in entrambi i sensi |
| `Copre (covers)` | Solo sorgente → destinazione | ISO A copre NIS2 art.21 → ISO propaga su NIS2, non viceversa |
| `Parziale`, `Correlato`, `Estende` | Non propagato | Richiedono valutazione separata |

**Cosa viene copiato:**
- Lo stato (`compliant` o `na`) sul controllo mappato dello stesso plant
- Per N/A: viene copiata anche la giustificazione (con riferimento al controllo sorgente)
- Viene generato un record nell'audit trail per ogni controllo aggiornato

**Propagazione multi-plant:**
Spuntando il checkbox **"tutti plant"** accanto al pulsante, la propagazione raggiunge tutti i plant che hanno un'istanza attiva del controllo di destinazione. Usa questa opzione quando una policy organizzativa è condivisa tra più siti (es. password policy, gestione accessi).

> Gli stati `gap`, `parziale` e `non_valutato` non sono propagabili: ogni plant deve valutarli autonomamente.

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

Se il plant è soggetto NIS2 l'incidente parte come **da valutare**: il CISO deve **confermare** l'obbligo di notifica — vengono allora impostate le scadenze T+24h e T+72h — oppure **escluderlo** con motivazione. Se l'incidente resta non classificato per più di **30 minuti**, il sistema invia un **alert di sollecito** al CISO per richiederne la classificazione (non decide al posto suo). Ogni decisione viene registrata nell'audit trail.

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
| **DO → CHECK** | Evidenza che documenta l'azione eseguita (obbligatoria): scegline una esistente oppure carica il file dalla stessa finestra, senza uscire dal ciclo. Il file caricato diventa un'evidenza del ciclo, sul sito del ciclo e senza scadenza |
| **CHECK → ACT** | Risultato della verifica (testo descrittivo) + Esito scelto: **ok** / **parziale** / **ko** |
| **ACT → CHIUSO** | Standardizzazione: documentazione della soluzione adottata perche' sia replicabile (minimo 20 caratteri) |

### Cosa succede se esito CHECK = ko

Se nella fase CHECK l'esito e' **ko** (la soluzione non ha funzionato):

1. Il ciclo non avanza ad ACT ma torna automaticamente alla fase **DO**
2. Viene aggiunta una nota nel log del ciclo con la data del fallimento
3. E' necessario compilare un nuovo piano d'azione per la fase DO
4. Il contatore di cicli DO viene incrementato per tracciare quante iterazioni sono state necessarie

Non c'e' un limite al numero di iterazioni DO-CHECK, ma il sistema segnala cicli con piu' di 3 iterazioni al Compliance Officer.

### Ciclo di sito o di organizzazione

Alla creazione il campo **Sito** indica a chi si applica il ciclo:

- un **sito**: il ciclo riguarda solo quello stabilimento e lo gestiscono gli utenti di quel sito;
- **Organizzazione — tutti i siti**: il ciclo vale per l'intera organizzazione (es. una procedura comune o una campagna di awareness per tutti). L'ambito diventa automaticamente **Organizzazione**.

I cicli di organizzazione sono visibili a tutti i siti, ma li aprono e li portano avanti (avanzamento di fase, modifica, archiviazione, cancellazione) solo gli utenti con accesso a tutta l'organizzazione; per gli altri compaiono in **sola lettura**, con il dossier consultabile. Filtrando l'elenco per un sito compaiono anche i cicli di organizzazione, che valgono anche lì; l'opzione **Solo organizzazione** mostra soltanto questi. Il filtro **Stato** mostra i cicli in corso (da PLAN ad ACT), una sola fase, i chiusi o gli archiviati. Nella fase DO di un ciclo di organizzazione si può allegare un'evidenza di qualunque sito. Alla chiusura anche la lesson learned generata è di organizzazione e, se il CHECK ha esito ko, il nuovo ciclo resta di organizzazione.

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

Se il ciclo PDCA è di organizzazione, anche la lesson learned è di organizzazione: la vedono tutti i siti, ma la gestiscono solo gli utenti con accesso a tutta l'organizzazione.

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

Il modulo guida il riesame di direzione richiesto da ISO/IEC 27001:2022 §9.3 e produce il verbale da archiviare e presentare all'auditor.

### Come creare un riesame

1. Vai su **Governance → Revisione Direzione → Nuova revisione**
2. Compila:
   - **Titolo**: es. "Riesame di direzione 2026"
   - **Sito**: un sito, oppure **org-wide** per un riesame dell'intera organizzazione (i dati aggregano tutti i siti e il verbale include un quadro per sito)
   - **Data riunione**
   - **Organo**: l'organo di governo che tiene il riesame (vedi [Governance → Organi di governo](#19-governance-m00)); viene proposto il CdA, se configurato. I convocati sono i componenti in carica dell'organo alla data del riesame, con il presidente dell'organo come presidente della riunione
   - Senza organo, viene proposto come presidente il CISO nominato in M00 Governance (quello del sito, altrimenti quello di organizzazione; in mancanza l'ISMS Manager)
3. Clicca **Crea revisione**: il sistema crea automaticamente l'ordine del giorno con i punti obbligatori

Dal dettaglio, fino all'approvazione, si gestiscono i **convocati e le presenze**: per ciascuno presente, assente o rappresentato da un delegato (con il nome del delegato), il ruolo e chi presiede, che deve risultare presente. Si possono aggiungere componenti dell'organo, utenti della piattaforma e **ospiti** senza account (es. un consulente), indicando nome e qualifica. **Riproponi dall'organo** ricarica i componenti in carica. Nel verbale nome e qualifica restano quelli alla data del riesame, anche se in seguito cambiano. Si possono modificare anche l'organo e la data del prossimo riesame.

### Ordine del giorno obbligatorio (ISO 27001 §9.3.2)

Ogni riesame contiene questi punti, che non si possono eliminare:

- a) Stato delle azioni dei riesami precedenti
- b) Cambiamenti nei fattori esterni e interni rilevanti per il SGSI
- c) Cambiamenti nelle esigenze e aspettative delle parti interessate
- d) Prestazioni della sicurezza delle informazioni (non conformità e azioni correttive, monitoraggio e misurazioni, audit, obiettivi)
- e) Feedback delle parti interessate
- f) Risultati della valutazione del rischio e stato del piano di trattamento
- g) Opportunità di miglioramento continuo

Si possono aggiungere punti extra con **Aggiungi punto**. **Non è possibile chiudere la riunione** se un punto obbligatorio non ha almeno una discussione o una decisione: i punti mancanti vengono evidenziati.

### Snapshot dei dati

Clicca **Genera snapshot dati** per congelare i dati GRC al momento della riunione. I dati compaiono dentro i punti dell'ordine del giorno a cui si riferiscono, con elenchi sintetici (massimo 10 voci, con «… e altri N»):

- **a)** azioni dei riesami precedenti: tutte quelle del riesame precedente, più quelle più vecchie ancora aperte o chiuse nel periodo, con quelle scadute in evidenza
- **d)** compliance per framework con i controlli in gap; KPI operativi fuori soglia; audit degli ultimi 12 mesi con readiness e non conformità aperte (maggiori prima); incidenti aperti e notificati NIS2; cicli PDCA fermi e task scaduti; documenti scaduti, in scadenza e approvati dall'ultimo riesame
- **f)** rischi critici (inerente → residuo, trattamento, owner, presenza del piano), rischi accettati formalmente, processi critici senza piano BCP
- **g)** opportunità di miglioramento emerse dagli audit

Lo snapshot si può rigenerare fino all'approvazione; dopo resta fisso perché è il contenuto del verbale.

### Come condurre la riunione e registrare le decisioni

1. Clicca **Avvia riunione**
2. Per ogni punto: aprilo, consulta i dati, scrivi la **discussione** e salva
3. Con **Aggiungi decisione** registra gli output del riesame (§9.3.3): descrizione, **tipo** (miglioramento, modifica al SGSI, risorse, altro), owner e scadenza
4. Se la decisione va eseguita, spunta:
   - **Crea task**: apre un task in M08 **assegnato al ruolo** scelto, con la scadenza della decisione (priorità alta per le modifiche al SGSI)
   - **Apri ciclo PDCA**: apre un ciclo PDCA in M11 (per un riesame di organizzazione scegli un sito oppure **Organizzazione (tutti i siti)**, riservato a chi ha accesso a tutta l'organizzazione)
   Lo stato del task e la fase del PDCA collegati si vedono sulla decisione
5. Clicca **Segna come completata**: il sistema verifica i punti obbligatori e propone la **data del prossimo riesame** secondo la policy dello scadenzario. Riunioni pianificate e prossimo riesame compaiono nello **Scadenzario**

### Sintesi executive con l'IA

La sintesi executive apre il verbale: giudizio complessivo sul SGSI, criticità, decisioni e priorità.

- **Scrivi a mano**, oppure
- **Genera bozza con IA** (richiede lo snapshot; conviene farlo dopo aver compilato l'ordine del giorno). Al motore IA arrivano dati aggregati e i testi del verbale: i nomi delle persone vengono sostituiti da segnaposto e il testo passa dall'anonimizzazione standard (email, telefoni, nomi dei siti). La bozza è marcata come **contenuto generato da IA** e **non entra nel verbale** finché non clicchi **Accetta nel verbale**, eventualmente dopo averla modificata; **Scarta bozza** la elimina

Nel verbale la sintesi riporta se è stata redatta con il supporto dell'IA (e con quale modello), se è stata modificata e chi l'ha accettata.

### Approvazione e verbale

1. L'approvazione ha due forme (richiedono snapshot generato e riunione completata):
   - **Approva in app**: la può dare un **componente in carica dell'organo con account collegato** (es. un consigliere), che vede e approva solo i riesami del proprio organo senza poterli modificare; nel verbale compaiono il suo nome e la sua qualifica. Può approvare anche la governance (Compliance Officer)
   - **Registra delibera dell'organo**: se l'organo ha deliberato fuori dalla piattaforma, la governance registra **numero e data della delibera** (non anteriore alla riunione) e, facoltativamente, il **documento M07** come evidenza; il verbale riporta «Approvato da <organo> — Delibera n. … del …» e chi l'ha registrata

   Dopo l'approvazione dati della riunione, convocati, ordine del giorno, decisioni e sintesi non sono più modificabili; resta aggiornabile solo lo stato di avanzamento delle decisioni
2. Scarica il verbale in **PDF** o **HTML**: dati del riesame, partecipanti, sintesi executive, punti di attenzione, ordine del giorno con dati, discussione e decisioni, riepilogo delle decisioni, approvazione. Il download è registrato nell'audit trail
   Sotto **Stato riunione** si sceglie il **logo del verbale**, in alto a destra nel PDF e nell'HTML, tra quelli caricati per i siti in Plant Registry (proposto quello del sito del riesame). Si può cambiare anche dopo l'approvazione
3. Il **pacchetto audit** (M03) include il riepilogo dei riesami e il verbale PDF di quelli approvati

### Riesame mirato

Fra un riesame completo e l'altro l'organo può riunirsi su punti specifici, per esempio per approvare una politica o decidere un piccolo cambiamento. Per queste sedute crea un riesame di tipo **Mirato** (scelta nel modulo di creazione, non modificabile dopo).

1. Il riesame mirato **non ha** i punti obbligatori del §9.3.2, lo snapshot dei dati, la sintesi executive né le bozze IA, e **non vale come riesame periodico**: la data del prossimo riesame resta quella decisa nell'ultimo riesame completo
2. **Documenti da decidere**: con **«Aggiungi documenti da decidere»** si apre l'elenco dei documenti del perimetro in bozza, in revisione o in approvazione, e di quelli in vigore con una nuova versione non approvata (badge *Obbligatorio*, *Nuova versione*, *Delibera dell'organo*). Ogni documento scelto diventa un punto dell'ordine del giorno, con la **revisione esaminata** fissata al momento della scelta
3. Per ogni documento registra l'**esito**: *Approvato*, *Rinviato* o *Respinto*, con eventuale nota nella discussione. Se dopo la scelta viene caricata una nuova revisione, il punto lo segnala: usa **«Riallinea»** (l'esito va registrato di nuovo, sul testo nuovo)
4. Aggiungi i **punti liberi** per le altre decisioni, come nel riesame completo (discussione, decisioni, task, PDCA)
5. **Chiudi la riunione**: serve almeno un punto e ogni documento deve avere un esito
6. **Approva il verbale** (in app o registrando la delibera): gli esiti si applicano ai documenti. Gli *approvati* entrano in vigore per delibera dell'organo, con la data della delibera o della seduta; i *respinti* tornano in bozza; i *rinviati* restano in attesa. Se un esito non si può applicare (per esempio è stata caricata una nuova revisione dopo la seduta) resta indicato con il motivo e si può ritentare
7. Il **verbale** del riesame mirato riporta i documenti esaminati con revisione ed esito, i punti e le decisioni; nel **pacchetto audit** le sedute mirate sono in `09_management_review/sedute_intermedie/`

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

La copertura (campione, esteso, completo) vale solo per gli audit lanciati da un **programma annuale**, dove la verifica è distribuita su più trimestri. Un audit creato singolarmente con **+ Nuova preparazione**, anche multi-sito, copre sempre **tutti i controlli** e non mostra la percentuale.

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

Le scadenze di risposta sono calcolate automaticamente dalla data di apertura del finding in base a queste policy. Per Major e Minor NC viene creato automaticamente un ciclo PDCA collegato al finding; per le Major NC anche un task urgente.

#### Collegare finding e PDCA

Ogni finding può avere **un solo PDCA**; un PDCA può coprire più finding, ma dello stesso audit e dello stesso sito (es. due osservazioni risolte con un'unica azione). Il collegamento è visibile da entrambi i lati: sul finding la fase del PDCA, con un clic per aprirlo; sul PDCA il finding e l'audit di origine, con tipo di audit e committente.

Dal tab **Finding** dell'audit, per un finding ancora senza PDCA:

- **Apri PDCA** crea il ciclo già collegato, sul sito dell'audit e con il tipo di audit (utile per osservazioni e opportunità, che non lo aprono in automatico);
- **Collega a PDCA esistente** lo collega a un ciclo aperto dello stesso sito.

Dal menù **PDCA** si può fare lo stesso: nel nuovo ciclo con origine **Audit** scegli audit e finding (sito e tipo di audit si compilano da soli), oppure dal pulsante **🔗 Finding** di un ciclo esistente. Un collegamento errato si rimuove con **Scollega**, indicando il motivo, che resta nell'audit trail.

**PDCA già esistenti, anche chiusi** — un finding si può collegare a qualunque PDCA dello stesso sito, **anche già chiuso o archiviato**: è il caso di un'azione correttiva svolta prima di registrare il finding (es. un PDCA aperto a mano dal rapporto dell'audit) o del recupero dello storico. Se il finding è aperto e il PDCA è chiuso, valgono le regole di chiusura del PDCA descritte sotto (con esito efficace il finding si chiude subito); se il finding è già chiuso non cambia nessuno stato (collegamento a posteriori, registrato come tale nell'audit trail). Dal menù PDCA, con **🔗 Finding**, si vedono tutti i finding dell'audit, aperti e chiusi.

**Sostituire un PDCA** — se il finding ha già un PDCA (per le NC quello aperto in automatico), lo si sostituisce con quello giusto indicando il motivo: dal finding con **Sostituisci PDCA**, oppure dal menù PDCA scegliendo il finding (compare con il ciclo a cui è collegato). Il PDCA sostituito viene archiviato solo se era stato aperto in automatico per quel finding e non ci si è mai lavorato; altrimenti resta com'è, solo scollegato. Per un finding chiuso non si apre un nuovo PDCA, lo si collega a uno esistente.

#### Come chiudere un finding

1. Nel tab **Finding** dell'audit clicca **Chiudi finding** sul rilievo
2. Inserisci le **note di chiusura** (per Major e Minor NC almeno 20 caratteri) e scegli l'**evidenza di chiusura** (obbligatoria per Major e Minor NC)
3. Clicca **Chiudi**

Se il finding ha un PDCA collegato, si chiude solo ad azione correttiva completata: con il PDCA **chiuso** (o archiviato), oppure in fase **ACT** se il PDCA copre solo questo finding; in quest'ultimo caso il PDCA viene chiuso insieme al finding e le note di chiusura diventano la sua standardizzazione. Negli altri casi il sistema indica la fase del PDCA e non salva nulla. **Chiusura dal PDCA** — il PDCA contiene già evidenza (fase DO), verifica di efficacia (CHECK) e standardizzazione (ACT), quindi quando lo chiudi i finding collegati seguono l'esito del CHECK: **efficace** → si chiudono con lui, con l'evidenza della fase DO e la descrizione ACT come note di chiusura (per una NC serve l'evidenza DO, altrimenti restano "in risposta"); **parzialmente efficace** → passano "in risposta" e la chiusura la decidi tu dal tab Finding; **non efficace** → passano al nuovo ciclo "[Riciclo]" e restano aperti. Non viene creata una Lesson Learned in più: basta quella del PDCA. Se un finding è rimasto "in risposta" con il PDCA già chiuso (ad esempio collegato prima di questa regola, o con esito parziale che ritieni sufficiente), il pulsante **Chiudi con il PDCA** lo chiude usando evidenza DO e descrizione ACT del PDCA, senza reinserirle.

#### Come scaricare la relazione audit

Dall'audit in corso o chiuso:
1. Clicca il pulsante **Report** in alto a destra nella pagina dell'audit
2. Scegli la lingua del report
3. Il sistema genera un report **HTML** con: riepilogo copertura, lista finding per tipo, stato di chiusura, trend rispetto all'audit precedente
4. Il report e' disponibile immediatamente per il download (stampabile/archiviabile)

---

### Audit esterni: seconda e terza parte

Oltre agli audit interni, in Audit Prep si registrano gli audit condotti da terzi, così i loro rilievi seguono lo stesso percorso (scadenze, PDCA, chiusura con evidenza):

- **Seconda parte (cliente)**: l'audit che un cliente (es. un OEM) svolge su di voi, direttamente o tramite un ente incaricato;
- **Terza parte (certificazione)**: l'audit di un ente di certificazione (es. TISAX, ISO/IEC 27001).

**Come registrarlo**

1. Clicca **+ Nuova preparazione** e scegli il **Tipo di audit**
2. Per la seconda parte indica il **Committente**, cioè il cliente per cui è svolto l'audit, e in **Ente / auditor** chi lo esegue; il framework è facoltativo
3. Aggiungi i finding come per un audit interno: se non indichi un auditor sul finding vale l'ente dell'audit, e il PDCA aperto per le non conformità riporta il tipo di audit (es. "Seconda parte")

Tipo e committente si possono correggere in seguito dal tab **Info audit**.

**Seconda parte: niente checklist.** Nell'audit di seconda parte i punti di verifica sono quelli del cliente: la checklist dei controlli non viene caricata (nemmeno scegliendo TISAX AL3), il dettaglio si apre sul tab **Finding** e la card mostra i rilievi aperti e se il rapporto è allegato, al posto della prontezza. Il framework, se indicato, vale solo come riferimento. Nella terza parte (certificazione) la checklist resta, perché l'ente verifica proprio i requisiti del framework.

**Audit interno affidato a un consulente esterno.** Se l'audit interno lo conduce un consulente, spunta **Condotto da un consulente esterno** (alla creazione o dal tab **Info audit**). L'audit resta interno, ma si gestisce come una seconda parte: niente checklist né prontezza, si registrano i rilievi del consulente e si allega il suo rapporto, che entra nel pacchetto audit (cartella AUDIT_ESTERNI).

**Titolo** — il titolo dell'audit si modifica con la matita accanto al nome, nel dettaglio. In un audit multi-sito si modifica il titolo dell'audit comune, riportato su ogni sito.

**Rapporto ufficiale** — nel tab **Info audit**, sezione **Rapporto ufficiale dell'auditor o dell'ente**, scegli il file (es. il PDF ricevuto dal cliente) e clicca **Allega rapporto**. Il file viene archiviato come evidenza di tipo "report", sul sito dell'audit e senza scadenza. Da lì puoi scaricarlo, sostituirlo con una revisione (il precedente resta tra le evidenze) o scollegarlo. È diverso da **Scarica relazione**, che è il riepilogo generato dalla piattaforma.

Gli audit esterni compaiono con il tipo e il committente nell'elenco, nell'analisi del riesame di direzione (risultati degli audit, §9.3.2 d) e nel verbale; il **pacchetto audit** contiene la cartella `AUDIT_ESTERNI/` con un riepilogo e i rapporti allegati.

### Audit su più siti

Un audit può riguardare alcuni siti ma non tutta l'organizzazione: ad esempio un assessment TISAX AL2 con un unico Scope ID su due stabilimenti. In questo caso:

1. Clicca **+ Nuova preparazione** e spunta **Audit su più siti**
2. Scegli almeno due siti: tra i framework compaiono solo quelli assegnati a **tutti** i siti scelti
3. Compila titolo, tipo, committente, ente, data ed eventuale **Scope ID** e crea l'audit

Il sistema crea **un audit per sito** (titolo "… — codice sito"), collegati tra loro:

- **per sito**: checklist, prontezza, finding con relativi PDCA, scadenze e task, e chiusura. Chi gestisce un solo sito vede e lavora solo il proprio;
- **in comune**: tipo, committente, ente, data, Scope ID e **rapporto ufficiale**, che si allega una sola volta ed è scaricabile da ogni sito. Si modificano dal tab **Info audit** di qualunque sito e valgono per tutti; serve però l'accesso a tutti i siti dell'audit.

**Rilievo comune** — nel form del finding spunta **Rilievo comune a tutti i siti dell'audit**: viene creato un finding per ogni sito, ciascuno con il proprio PDCA, contrassegnati come **Comune ai siti**. Senza la spunta il finding resta sul sito in cui lo registri.

**Correggere un finding** — con **✎ Modifica** nella card del finding correggi titolo e descrizione (es. un refuso). In un rilievo comune la correzione vale per tutti i siti. Tipo, date e stato non si modificano: passano da PDCA e chiusura. Negli audit archiviati i finding non si modificano più.

**PDCA comune** — per una non conformità comune, chi ha accesso a tutta l'organizzazione vede anche la spunta **Un solo PDCA di organizzazione per tutti i siti** (attiva di default): invece di un PDCA per sito se ne apre uno solo, di organizzazione, collegato al finding di ogni sito. Su un rilievo comune già registrato, il pulsante **PDCA comune a tutti i siti** fa lo stesso: sostituisce (e archivia) i PDCA automatici non ancora lavorati, mentre i siti con un PDCA già in lavorazione restano com'erano e vengono segnalati. Da **Collega a PDCA esistente** si può scegliere anche un PDCA di organizzazione: il collegamento vale per il rilievo su tutti i siti. Alla chiusura del PDCA comune i finding di tutti i siti si chiudono secondo l'esito del CHECK, come per un PDCA di sito.

Nel riesame di direzione di organizzazione l'audit su più siti conta **una volta**, con l'elenco dei siti coinvolti; nel riesame di un sito compare il solo audit di quel sito.

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

Il modulo si apre da **Operazioni → Fornitori** ed è organizzato in cinque tab: **Fornitori**, **Questionari**, **Template questionario**, **Stato NDA** e **Impostazioni valutazione**. Creano e modificano i fornitori Super Admin, Compliance Officer, Risk Manager e Plant Manager; gli auditor interni ed esterni li consultano in sola lettura. Ogni utente vede i fornitori dei propri siti e quelli senza sito associato (fornitori dell'intera organizzazione).

### Come registrare un fornitore

1. Nel tab **Fornitori** clicca **+ Nuovo fornitore**
2. Compila:
   - **Denominazione (ragione sociale)**, **CF / P.IVA** e **Paese sede legale** — obbligatori
   - **Email fornitore (TO)** — obbligatoria, è il destinatario dei questionari; in **Email aggiuntive (CC)** puoi aggiungere altri contatti in copia
   - **Descrizione fornitura** — cosa fornisce; serve anche al suggerimento dei codici CPV
   - **Livello rischio** — la tua stima iniziale; la valutazione vera arriva dalle fonti descritte più avanti
   - Sezione **ACN / NIS2**: **codici CPV** della fornitura (con il pulsante IA puoi farti suggerire i codici dalla descrizione, che viene inviata senza il nome del fornitore; ogni suggerimento va accettato a mano), flag **Fornitore NIS2 rilevante** e, se attivo, **criterio di rilevanza** (fornitura ICT strutturale, non fungibilità o entrambi) e **% di concentrazione** della fornitura
   - Sezione **TISAX**: flag **Fornitore rilevante TISAX** se tratta informazioni del perimetro TISAX (es. dati o prototipi dei clienti OEM) o accede ai sistemi in scope (VDA ISA 6.1.1)
3. Clicca **Crea fornitore**

**Controllo duplicati** — mentre compili il form il sistema cerca fornitori già registrati:

- **Stessa P.IVA** (confrontata ignorando spazi, punti, trattini e prefisso paese, es. `IT 0123.4567.890` = `01234567890`): il salvataggio è **bloccato**. Se il fornitore esistente è nel tuo perimetro puoi aprirlo con **Apri**; se è registrato su un sito fuori perimetro ne vedi solo l'esistenza e devi chiedere a un Compliance Officer di associarlo al tuo sito. Un fornitore eliminato non blocca il reinserimento.
- **Ragione sociale simile** (ignorando maiuscole, punteggiatura e forme societarie come S.r.l., S.p.A., GmbH): compare un **avviso** con i fornitori simili; per creare comunque spunta **Ho verificato: è un fornitore diverso**. L'audit trail registra quanti nomi simili erano presenti alla creazione.

Con l'icona di modifica cambi i dati e lo **Stato** del fornitore (attivo, sospeso, terminato). L'eliminazione è logica (il fornitore resta nello storico) e porta con sé i suoi questionari.

**Concentrazione** — la percentuale determina la soglia TPRM (ACN Delibera 127434): sotto il 20% **bassa**, dal 20% al 50% **media**, oltre il 50% **critica**. Quando un fornitore entra nella soglia critica il sistema invia una notifica, una sola volta finché la concentrazione non rientra.

### Elenco fornitori

L'elenco mostra per ogni fornitore CF/P.IVA, paese, concentrazione, **Rischio Adj**, stato, data e scadenza dell'ultima valutazione. Puoi cercare per denominazione, CF/P.IVA o email e filtrare per rischio, stato, rilevanza NIS2 e rilevanza TISAX; il filtro **Rischio** lavora sul Rischio Adj e l'opzione **Non valutati** elenca i fornitori senza alcuna valutazione.

**↓ Esporta CSV** scarica tutti i fornitori, solo i NIS2 rilevanti o solo i TISAX rilevanti, con codici CPV, criterio NIS2, concentrazione e date di valutazione.

Cliccando sul nome si apre il dettaglio del fornitore, con tre sezioni: **Valutazione interna**, **Audit terze parti** e **NDA / Contratti**.

### Come si calcola il rischio (Rischio Adj)

Il **Rischio Adj** è la classe peggiore (basso, medio, alto, critico) fra tre fonti, ognuna considerata solo se presente:

1. la **valutazione interna** corrente;
2. l'ultimo **questionario** valutato e non scaduto (inviato dalla piattaforma o valutazione esistente registrata);
3. l'ultimo **audit terze parti** approvato entro la validità configurata.

Se il fornitore è NIS2 rilevante e la concentrazione è critica, la classe sale di un livello (se l'opzione è attiva nelle impostazioni). Senza nessuna fonte il fornitore risulta **non valutato**. Il ricalcolo avviene a ogni nuova valutazione e ogni notte, così una valutazione scaduta smette di contare da sola.

### Valutazione interna

Dal dettaglio del fornitore, sezione **Valutazione interna**, clicca **Avvia valutazione** (o **Nuova valutazione**) e assegna un punteggio da 1 (rischio minimo) a 5 (rischio massimo) a sei parametri: **Impatto business**, **Accesso sistemi**, **Dati trattati**, **Dipendenza fornitore**, **Integrazione IT** e **Compliance certificazioni cyber**. L'anteprima mostra lo score ponderato e la classe risultante prima di salvare. Ogni nuova valutazione sostituisce la precedente, che resta nello **Storico valutazioni**.

### Questionari

**Template** — nel tab **Template questionario** prepari una o più email tipo: nome, **URL del form** del questionario (ad esempio un modulo online), oggetto e testo. Nell'oggetto e nel testo `{supplier_name}` diventa il nome del fornitore; nel testo `{questionnaire_link}` diventa il link al form; se nel testo manca, il link viene aggiunto in fondo all'email.

**Invio** — dall'elenco fornitori clicca **Quest.**, scegli il template e clicca **Invia**. L'email parte all'indirizzo TO del fornitore con in copia le email CC. Il fornitore compila il form esterno: la piattaforma non riceve le risposte in automatico.

**Solleciti** — ogni lunedì chi ha inviato i questionari riceve un'unica email di riepilogo con quelli senza risposta da più di 7 giorni. Dal tab **Questionari** puoi **Reinviare** il questionario; dal 3° invio senza risposta l'elenco segnala di contattare direttamente il fornitore.

**Valutazione** — quando hai letto le risposte, nel tab **Questionari** clicca **Valuta** e indica **data di valutazione**, **valutazione** (livello di rischio) ed eventuali note. La scadenza si calcola con la validità dei questionari configurata nelle impostazioni (12 mesi di default).

Il tab **Questionari** riepiloga in alto le valutazioni valide, quelle in scadenza nei 90 giorni, i questionari in attesa di risposta e quelli scaduti: cliccando un riquadro filtri l'elenco.

**Registrare una valutazione esistente** — per i fornitori già valutati prima di usare la piattaforma, o con un questionario raccolto su carta:

1. Dal tab **Questionari** (oppure dalla scheda del fornitore) clicca **Registra valutazione esistente**
2. Indica fornitore, **data** della valutazione (non futura) ed **esito** (livello di rischio)
3. Nel campo **Riferimento / note** (obbligatorio) scrivi dove si trova la valutazione e chi l'ha compilata: è ciò che mostrerai all'auditor
4. Clicca **Registra**. Nessuna email viene inviata al fornitore; nel tab Questionari la voce compare con l'etichetta **Registrata**

### Data di valutazione e scadenza

La data di valutazione **non si inserisce nell'anagrafica**: il sistema la ricava dall'ultima valutazione registrata, che può essere:

- l'esito di un **questionario** inviato dalla piattaforma (tab **Questionari → Valuta**);
- una **valutazione esistente**, cioè svolta fuori dalla piattaforma;
- un **audit terze parti** approvato.

La **scadenza** si calcola con la validità configurata in **Impostazioni valutazione** (12 mesi di default). L'elenco fornitori mostra data, origine e scadenza; lo scadenzario propone la voce **Rivalutazione fornitori** in prossimità della scadenza e apre un promemoria al Compliance Officer.

### Audit terze parti: pianificato → completato → approvato / rifiutato

Per i fornitori sottoposti a un audit (tuo o di un ente terzo), dal dettaglio del fornitore, sezione **Audit terze parti**:

1. **+ Nuovo audit**: indica la data e clicca **Registra**. L'audit è **Pianificato**
2. **Completa**: inserisci i punteggi 0–100 di **Governance**, **Security** e **BCP** e i **findings**. Lo score **Overall** è la media dei punteggi inseriti. Al completamento il livello di rischio del fornitore si aggiorna (Overall ≥ 75 basso, ≥ 50 medio, sotto 50 alto) e parte la notifica di audit completato
3. **Approva** o **Rifiuta**: chi rivede l'audit registra le note; per il rifiuto la motivazione è obbligatoria (almeno 10 caratteri)

Solo un audit **approvato** entra nel Rischio Adj, e solo entro la validità degli audit configurata (12 mesi di default): Overall ≥ 75 basso, ≥ 50 medio, ≥ 25 alto, sotto 25 critico. Un audit rifiutato resta nello storico ma non conta.

| Dimensione | Cosa valuta |
|-----------|-------------|
| **Governance** | Struttura organizzativa per la sicurezza, politiche interne, responsabilità definite, audit interni |
| **Security** | Controlli tecnici implementati, gestione vulnerabilità, incident response, certificazioni (ISO 27001, TISAX) |
| **BCP** | Piani di continuità operativa, RTO/RPO dichiarati, test di continuità eseguiti, ridondanze infrastrutturali |

### NDA e contratti

Dal dettaglio del fornitore, sezione **NDA / Contratti**, clicca **+ Carica NDA**, scegli il file e indica **titolo** ed eventuale **scadenza**. Il documento viene archiviato nel modulo Documenti come contratto collegato al fornitore; dalla stessa sezione lo scarichi o, se non è approvato, lo approvi.

Il tab **Stato NDA** riassume la copertura dei fornitori attivi: con NDA attivo, in scadenza nei 90 giorni, scaduto, in bozza o mancante. Puoi cercare per fornitore e filtrare per stato NDA e rischio.

### Impostazioni valutazione

Il tab **Impostazioni valutazione** raccoglie i parametri del calcolo: **pesi** dei sei parametri della valutazione interna (la somma deve essere 1,00), **etichette dei livelli** per ogni parametro, **soglie** dello score ponderato per le classi medio, alto e critico, **validità** dei questionari e degli audit terze parti (in mesi) e l'opzione **bump NIS2 + concentrazione critica**. Chi usa il modulo può consultarle, solo il Super Admin può modificarle.

---

## 14. Formazione (M15)

La piattaforma **non eroga** i corsi e non si collega a piattaforme di e-learning o di simulazione phishing: **governa** la formazione. Per ogni sito si pianifica cosa fare, si registra ogni erogazione con il **file di prova** e si misura la copertura del personale **solo in numeri**. È quello che chiedono ISO 27001 A.6.3 e cl. 7.2, NIS2 art. 21.2.g, ACN PR.AT e TISAX ISA 2.1.3: un piano, la prova che è stato eseguito e la copertura raggiunta.

Vai su **Operazioni → Formazione** e seleziona il sito in alto. La pagina ha quattro tab: **Piano**, **Erogazioni**, **Gruppi destinatari**, **Catalogo corsi**.

### Chi fa cosa

- **Registrano** gruppi, piani ed erogazioni il Compliance Officer e il Plant Manager del sito, oppure chi ha la **nomina di CISO** in Governance per il sito o per l'organizzazione. Non c'è assegnazione: registra chi arriva prima.
- **Leggono** piano, erogazioni e copertura anche l'Internal Auditor e l'Auditor Esterno: sono numeri e file di prova, non dati personali. Per i ruoli critici e il CdA vedono anche i nomi dei partecipanti, gli stessi già presenti in Governance: sono la prova richiesta da NIS2 art. 20.
- Gli altri ruoli vedono solo il **Catalogo corsi**.

### 1. Catalogo corsi

Per ogni corso indica:

- **Tipo**: corso, campagna di sensibilizzazione o simulazione di phishing;
- **Destinatari**: personale, ruoli critici o organo di gestione;
- **Validità (mesi)**: dopo quanti mesi l'erogazione va ripetuta (es. 12 = ogni anno); vuoto = non scade;
- **Obbligatorio**: i corsi obbligatori per il personale entrano nella copertura;
- **Ambito**: **organizzazione**, se il corso vale per tutti i siti (es. igiene standard: lo inserisci una volta sola), oppure **solo alcuni siti** per i corsi specifici. I corsi di organizzazione li gestisce chi ha un perimetro di organizzazione; un plant manager crea e modifica i corsi dei propri siti. Nel piano e nelle erogazioni di un sito compaiono i corsi di organizzazione e quelli di quel sito.
- **Competenza attribuita** e **livello** (solo per ruoli critici e organo di gestione, facoltativa): chi partecipa con un account riceve questa competenza nella propria scheda competenze (ISO 27001 cl. 7.2). I nomi proposti sono quelli dei requisiti di competenza dei ruoli.

Un corso già in un piano o con erogazioni non si elimina: si **archivia**.

**Controlli provati dalle erogazioni.** In cima al catalogo c'è un'impostazione unica, valida per tutti i corsi: per ogni tipo di destinatari, quali controlli prova un'erogazione (es. personale → ACN PR.AT-01, ISO A.6.3, TISAX ISA-2.1.3; ruoli critici → ACN PR.AT-02). La modifica chi gestisce l'organizzazione, cercando il controllo per codice; gli altri la vedono in sola lettura. Non si scelgono i controlli corso per corso e i framework non vengono modificati. I valori iniziali si caricano con il comando `load_training_evidence_controls`.

### 2. Gruppi destinatari

Per il sito inserisci i gruppi di persone da formare con il loro **numero** (es. «Produzione: 240», «Uffici: 45»). Non si inseriscono nomi né dati dei dipendenti. Quando il numero cambia, aggiornalo: la data di aggiornamento si imposta da sola. Un gruppo non riverificato da oltre 6 mesi è segnato **da riverificare**, perché la copertura si calcola su quel numero.

### 3. Piano formativo

1. Nel tab **Piano** scegli l'anno e clicca **Crea il piano del sito** (chi gestisce l'organizzazione può creare anche il **piano di organizzazione**, che vale per tutti i siti).
2. Clicca **Collega documento** e scegli il documento del piano gestito in **Documenti**: l'approvazione segue il workflow documentale. Il piano approvato è il documento richiesto da ISO 27001 A.6.3.
3. Clicca **Aggiungi voce** per ogni attività: corso, scadenza e gruppi destinatari.

Ogni voce mostra lo stato (**Pianificata**, **In scadenza** entro 30 giorni, **In ritardo**, **Svolta**), il numero di erogazioni e la copertura raggiunta.

**Promemoria.** Ogni mattina, per le voci senza erogazioni in scadenza entro 30 giorni o già in ritardo, viene aperto un **task al Compliance Officer** del sito e inviata una notifica a chi segue la formazione. Il task si chiude da solo quando registri l'erogazione. Le scadenze delle voci compaiono anche in **Activity Schedule**.

### 4. Registrare un'erogazione

1. Nel tab **Erogazioni** clicca **Registra erogazione**.
2. Scegli il corso e la data. La voce del piano viene riconosciuta da sola; se ce n'è più di una puoi sceglierla.
3. Seleziona i gruppi coinvolti e inserisci le **persone formate**. Le persone da formare sono proposte dalla somma dei gruppi e si possono correggere.
   Per una **simulazione di phishing** inserisci invece le e-mail inviate, i clic e le segnalazioni.
4. Allega il **file di prova** (registro presenze, export dell'e-learning, report della campagna). È obbligatorio: i nomi dei partecipanti stanno solo nel file, la piattaforma registra i numeri.
5. Clicca **Registra**.

Dal file nasce un'**evidenza** con scadenza pari alla validità del corso, **collegata automaticamente ai controlli impostati per i destinatari del corso**, sul sito dell'erogazione e **solo per i framework applicati al sito** (es. ACN PR.AT-01 solo sui siti NIS2, ISA-2.1.3 solo su quelli TISAX). Il messaggio di conferma indica quanti controlli sono stati collegati ed elenca quelli di un framework applicato ma non istanziati o esclusi dallo SOA.

Il file di prova non si sostituisce: se è sbagliato, elimina l'erogazione e registrala di nuovo. Un'erogazione la cui prova sostiene controlli già valutati non si elimina (solo un superuser può farlo). Le righe **storico senza prova** vengono dalla migrazione dei vecchi dati per persona: riportano solo i conteggi.

### 5. Ruoli critici e organo di gestione

Per i corsi con destinatari **ruoli critici** o **organo di gestione** l'erogazione registra **chi ha partecipato**, non i gruppi:

1. Nel form di registrazione, dopo il corso e la data, compaiono due elenchi: i **titolari di nomine** attive sul sito (con le loro nomine) e i **componenti in carica degli organi di governo** del sito o di organizzazione (i componenti del CdA hanno l'etichetta CdA). Gli elenchi dipendono dalla data dell'erogazione: compare chi era in carica quel giorno.
2. Spunta chi ha partecipato. Le persone formate sono il numero dei partecipanti (una persona che è sia componente sia titolare di nomine conta una volta); le persone da formare, se non le indichi, sono lo stesso numero.
3. Allega il file di prova (foglio firme, attestati) e registra.

Se il corso attribuisce una **competenza**, chi ha un account la riceve con la prova dell'erogazione e la stessa scadenza. Un livello più alto già posseduto non viene abbassato. Se elimini l'erogazione, la competenza torna com'era prima. I partecipanti non si modificano: se sono sbagliati, elimina l'erogazione e registrala di nuovo.

**Formazione dell'organo di gestione (NIS2 art. 20).** Nel tab **Erogazioni** un riquadro elenca i componenti in carica degli organi di tipo CdA del sito o dell'organizzazione: in verde chi ha una formazione valida (con la data fino a cui vale), in rosso chi è ancora da formare. Conta la partecipazione a un corso con destinatari «organo di gestione» ancora valido. I componenti si gestiscono in **Governance → Organi di governo**.

### Dove si vedono i risultati

- **Reporting → KPI**, sezione «Formazione e consapevolezza»: copertura per corso e sito, avanzamento del piano, voci in ritardo, ultime simulazioni di phishing e formazione da ripetere.
- **KPI** calcolati in automatico, agganciabili agli **obiettivi di sicurezza**: copertura della formazione obbligatoria, avanzamento del piano, voci in ritardo, tasso di clic e di segnalazione del phishing, formazione dell'organo di gestione.
- **Centro Operativo**: segnala le voci del piano in ritardo.
- **Pacchetto audit** (Audit Preparation): cartella `07_training` con piano, erogazioni con il riferimento all'evidenza, copertura e gruppi del sito, partecipanti delle erogazioni per ruoli critici e CdA, stato della formazione del CdA (`board_training.csv`).

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

### Organi di governo (CdA, comitato, direzione)

Vai su **Governance → Ruoli & organi** e scorri fino a **Organi di governo**. È l'anagrafica di chi tiene e approva il riesame di direzione (ISO 27001 §5.1, §9.3).

1. **+ Nuovo organo**: nome, **tipo** (Organo di amministrazione — CdA, Comitato sicurezza, Direzione), **perimetro** (intera organizzazione, oppure i siti che governa: con più entità giuridiche si crea un organo per ciascuna) e mandato. Il CdA è marcato come **organo di gestione NIS2** (art. 20: approva le misure di gestione del rischio, ne risponde ed è tenuto a formarsi)
2. **+ Componente**: nome e cognome, qualifica (es. Amministratore Delegato), ruolo nell'organo (presidente, membro, segretario), inizio ed eventuale fine della carica. L'**account** è facoltativo: collegarlo permette alla persona di approvare dall'app i riesami di questo organo. Non serve creare account solo per scrivere un nome nel verbale
3. Chi lascia l'organo si chiude con **Chiudi carica** (data di fine), non si elimina: resta nei verbali passati e tra gli **ex componenti**. **Elimina** serve solo a correggere un inserimento errato e non è consentito se il componente compare in un riesame

Regole: un solo presidente in carica per volta; lo stesso account non può essere collegato a due componenti dello stesso organo nello stesso periodo. Gestiscono gli organi Super Admin e Compliance Officer, solo per organi il cui perimetro rientra interamente nel proprio; gli altri ruoli li consultano per i siti del proprio perimetro. Componenti e segnalazioni (account disattivato, carica in scadenza, presidente mancante) compaiono anche in **Reporting → Accessi & responsabilità** e nel pacchetto audit.


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

### Generare un report

1. Seleziona il tipo di report (gap TISAX, compliance NIS2, SOA ISO 27001, BIA executive)
2. Scegli il plant e il periodo
3. Seleziona la lingua del report
4. Clicca **Genera** — il report viene prodotto nel formato previsto: **HTML** per i report di sintesi, **CSV/Excel** per gli export tabellari (SOA, VDA ISA, NIS2 matrix)
5. Il report e' disponibile per il download nella sezione **Report generati**

Tutti i report generati sono registrati nell'audit trail.

---

## Centro Operativo (M21)

[Schermata: cockpit con insight prioritizzati e postura]

Il Centro Operativo è il cruscotto che aggrega i segnali di tutti i moduli in **insight** prioritizzati e ti mostra la **postura di sicurezza** complessiva con il relativo trend. È pensato per il lavoro quotidiano: ti dice *cosa guardare per primo* senza dover aprire modulo per modulo.

### Cosa sono gli insight

Ogni insight è una segnalazione generata dagli **advisor** (regole che osservano controlli, rischi, incidenti, scadenze, audit, ecc.) con una priorità. Per ogni insight vedi una sintesi, il modulo di origine e l'azione consigliata.

### Gestire un insight (anti alert-fatigue)

Dalla scheda dell'insight puoi:

- **Accetta**: prendi in carico l'insight fino a una data — non riappare fino ad allora
- **Posponi (snooze)**: lo metti in pausa fino a una data, con nota facoltativa
- **Riapri**: riporti attivo un insight precedentemente accettato o posposto

Queste azioni evitano che gli stessi avvisi si ripetano all'infinito e vengono registrate nell'audit trail.

### Spiegazione AI e assistente

Se il modulo AI (M20) è attivo, puoi chiedere una **spiegazione AI** dell'insight (i dati vengono anonimizzati prima dell'invio) e usare l'**assistente operativo** per domande sul contesto. L'AI non applica mai modifiche da sola: vale sempre il principio human-in-the-loop.

### Postura e trend

La pagina mostra un indicatore di postura complessiva e il suo andamento nel tempo (posture trend), utile per capire se la situazione sta migliorando o peggiorando.

### Chi può accedere

Il Centro Operativo è riservato ai ruoli di governance e supervisione: Super Admin, Compliance Officer, Risk Manager, Internal Auditor e Plant Manager. Non è accessibile all'Auditor Esterno.

---

## OSINT Monitor

[Schermata: dashboard esposizione OSINT]

OSINT Monitor è il modulo trasversale che monitora l'**esposizione esterna** della tua organizzazione — i tuoi domini e i siti web dei fornitori — usando fonti pubbliche (Open Source Intelligence). A differenza degli altri moduli non è legato a un singolo plant: lavora a livello di **organizzazione**.

### Cosa monitora

- Il **dominio principale** e gli eventuali **domini aggiuntivi** configurati
- I **siti web dei fornitori** (M14), come entità OSINT di tipo *supplier*
- Per ogni entità: sottodomini, certificati SSL, record DNS/WHOIS e — se configurate le chiavi — reputazione, breach, blacklist e threat intelligence

### Scansioni ed enricher

Le scansioni di base (SSL, DNS, WHOIS) sono **gratuite e sempre attive**. Gli arricchimenti aggiuntivi (HaveIBeenPwned, VirusTotal, AbuseIPDB, Google Safe Browsing, AlienVault OTX, abuse.ch) si abilitano inserendo le rispettive **chiavi API** in **OSINT → Impostazioni** (tutte opzionali; usa il pulsante `?` della pagina impostazioni per i link di registrazione). Le chiavi sono cifrate e mai mostrate in chiaro.

### Alert e azioni automatiche

Quando una scansione rileva un problema rilevante:

- Un **alert critico su un tuo dominio** può generare automaticamente un **incidente** (M09)
- Un **alert su un fornitore** può generare un **task di verifica** (M08) al referente interno
- I finding possono essere instradati alla remediation e, se necessario, **escalati**

Le notifiche di esposizione esterna sono destinate **solo al personale interno** (mai all'Auditor Esterno).

### Analisi AI

Se il modulo AI (M20) è attivo, puoi richiedere analisi della superficie di attacco, briefing NIS2 e report per la direzione: i dati vengono **anonimizzati** prima dell'invio al provider AI.

### Chi può accedere

OSINT Monitor è riservato a Super Admin, CISO e Compliance Officer.

---

## Appendice: Domande frequenti

**Non trovo un controllo che dovrebbe essere nel mio framework.**
Verifica di aver selezionato il plant corretto nel selettore in alto. Se il framework e' attivo per quel plant ma il controllo non appare, contatta il Compliance Officer — potrebbe non essere stato generato durante l'attivazione del framework.

**Ho caricato un'evidenza ma il controllo mostra ancora "gap".**
Verifica che l'evidenza sia collegata al controllo corretto (scheda evidenza → sezione "Controlli coperti") e che la data di scadenza non sia gia' passata.

**Il timer NIS2 e' partito ma l'incidente non e' davvero un incidente NIS2.**
Se sei il CISO, apri la scheda incidente ed **escludi l'obbligo NIS2** inserendo la motivazione: le scadenze decadono e la decisione viene registrata nell'audit trail. Finché l'incidente resta "da valutare", dopo 30 minuti ricevi un alert di sollecito alla classificazione.

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
