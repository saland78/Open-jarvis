# OpenJarvis personale: chat e note locali separate

Stato al 2026-10-04: **aggiornamento installato, compilazione completa sul Mac e collaudo della nota reale superati**. La revisione del significato conferma i quattro fatti selezionati e la frase corrente completa con le indicazioni di consultazione. Esito circoscritto al caso e al formato riconosciuto; nessuna verifica esterna o garanzia su altre sintesi. Questo difetto è chiuso nel caso collaudato; il prossimo task riguarda la latenza, senza perdere informazioni o controlli.

Il [confronto compatto sul Mac](qualification-compact-wire-experiment.md#confronto-reale-concluso-e-superato--2026-10-04) è concluso: quattro risposte, entrambe le coppie superano le soglie native e la revisione del significato. Token generati ridotti del 48,6–51,0%, durata nativa di produzione del 51,7–55,5%. Nessuna misura causale del primo testo nel browser; cache e caricamento riportati separatamente. L'errore iniziale del comando è corretto e chiuso senza ripetere inferenze già eseguite.

Il [trasporto compatto](qualification-compact-wire-production.md#collaudo-reale-concluso-e-superato--2026-10-04) è **installato e collaudato sul Mac**: due sorgenti verificati con backup, avvio riuscito, una sintesi reale accettata e quattro fatti riesaminati favorevolmente. Testo nell’interfaccia a **26,381 s**; recupero nota 3,10 ms, caricamento Ollama 5,08 s, contesto 11,90 s, produzione 9,33 s per 67 token. Metriche lette dalla stessa richiesta senza un’altra inferenza. Confronto osservato con la precedente richiesta di circa 45,29 s, senza garanzia causale o universale. I [numeri filtrati](qualification-compact-wire-production-mac-2026-10-04.json) non contengono testo delle note, percorsi personali o cronologia del Terminale.

Tre stringhe del modello, frase corrente e date dai passaggi comprovati, quattro punti finali; origini, validatori e rilettura conservati. **178 controlli di sviluppo già passati** (168 regressioni e 10 del manifest), PR sempre draft. Questo task è concluso nell’ambito definito: nessun altro test, reinstallazione o cambio del modello necessario per la sua chiusura. Le funzioni future seguono la [roadmap dei moduli](future-capabilities-roadmap.md).

Repository: https://github.com/saland78/Open-jarvis

Sorgente: https://github.com/open-jarvis/OpenJarvis, commit `c4da16e1ca3d21f4cc1905d4200063e564104f0f` (1 ottobre 2026). Il fork conserva storia, licenza Apache-2.0 e relazione upstream. `main` conserva la base; queste modifiche sono su `feature/andrea-local-profile`, PR draft #1. Il precedente Jarvis rimane in un'altra repository e cartella.

La [serie sul contesto](qualification-context-prompt-experiment.md#esito-mac-della-serie-finita--2026-10-04) è conclusa: quattro risposte corrette nell’ambito riesaminato e circa 29% di token di input in meno. Soglia prestazionale originale non superata per cache; nessuna adozione o ripetizione della serie. Prossimo passo nello stesso task: [diagnosi distinta di due richieste con prefissi isolati](qualification-prefill-isolation-diagnostic.md), preparata e verificata, Mac ancora da eseguire. Produzione invariata.

## Prima versione

`Avvia-OpenJarvis.command` prepara un ambiente Python nel progetto, compila l'estensione Rust e l'interfaccia quando le sorgenti cambiano, quindi avvia la chat su **http://127.0.0.1:8008**. Il browser si apre dopo il controllo di salute del backend. Lascia aperto quel Terminale; Control+C ferma OpenJarvis. Un'altra istanza sulla stessa porta produce un messaggio e non viene terminata.

Il profilo usa esclusivamente Ollama a `127.0.0.1:11434`, con `qwen3:4b-instruct-2507-q4_K_M`, italiano, temperatura 0,4, contesto 4096 e massimo 512 token di risposta. Il backend impone questi limiti anche se le impostazioni del client o la classificazione della complessità upstream suggeriscono altri valori. La lista dell'interfaccia mostra soltanto il modello configurato, se installato. Nessun fallback cloud viene costruito.

Dati e cache di compilazione sono in `~/.openjarvis-andrea`, distinti dai dati del precedente Jarvis. L'avvio non importa il vecchio `.env`, i database, le skill o le note Obsidian. L'ambiente runtime non eredita credenziali cloud o altre configurazioni OpenJarvis. Le conversazioni della UI sono conservate dal browser per questa origine; ciò non costituisce apprendimento del modello.

Questa fase abilita **chat di testo**, con streaming, timeout di 90 secondi e una generazione per volta. È disponibile anche un pannello Obsidian in sola lettura; soltanto la sua configurazione locale può essere salvata. Le altre richieste di modifica vengono rifiutate; gli strumenti hanno una policy esplicita senza concessioni e con deny globale. Memoria automatica, scheduler, canali, apprendimento, skill discovery e ingestion automatica dei connettori restano disattivati. Il codice completo upstream rimane disponibile per le integrazioni successive. I relativi menu originali possono essere ancora visibili: la loro presenza non indica che la funzione sia già attiva.

La build locale ignora URL API esterni salvati o configurati e disattiva analytics, leaderboard e relativo invito alla condivisione. Il codice originale resta disponibile nelle normali build upstream. Questo profilo non è una sandbox del sistema operativo: i processi Python/Rust hanno i permessi dell'utente che li avvia.

## Installazione sul Mac: prima verificare i requisiti

Non sostituire la cartella del Jarvis attuale. Scaricare in seguito **il branch della PR**, in una nuova cartella; `main` non contiene ancora il launcher. Non copiare configurazioni o dati personali nel fork pubblico.

Requisiti da controllare prima dell'avvio:

- Node >=22.22 e npm disponibile. Il launcher usa npm **11.19.0 per questo progetto**, senza aggiornare globalmente la versione già installata.
- `uv` disponibile. Il launcher richiede Python 3.12 con le dipendenze server del lock upstream; uv può scaricare Python se necessario.
- Cargo/Rust >=1.88 e gli strumenti di compilazione Apple/Xcode Command Line Tools. Il launcher segnala Cargo assente senza installarlo automaticamente.
- Ollama avviato e il modello configurato installato.

La prima preparazione scarica dipendenze e compila codice nativo, quindi richiede Internet e può durare diversi minuti. Rust viene compilato in una cache nuova, separata dai target di altre build. `uv sync --inexact` conserva l'estensione compilata localmente. L'avvio del modello e la sua latenza dipendono dal Mac; non usare simultaneamente i due Jarvis per un confronto delle prestazioni.

Procedere con installazione e primo avvio sul Mac soltanto dopo il controllo guidato dei requisiti. Non è ancora disponibile un collaudo macOS Intel della nuova versione.

## Verifiche completate

Ambiente di sviluppo Linux x86_64, Python 3.12.14, Rust 1.88.0. Nessun dato personale o modello reale utilizzato.

| Controllo | Esito e limite |
| --- | --- |
| Dipendenze Python server con lock upstream | Installazione completata |
| Estensione Rust reale | Compilazione release con Cargo.lock, import e costruzione del backend riusciti |
| Build frontend | TypeScript e Vite completati; rimangono avvisi upstream sulle dimensioni dei bundle |
| Test runtime | 14 passati: ambiente, origine, policy, budget, concorrenza, timeout, cancellazione, accesso al vault, provenienza e aggiornamenti |
| Test frontend | 11 passati su due file: URL locali, servizi esterni, modello configurato, errori, eventi SSE divisi tra chunk e telemetria engine |
| Chat nel browser | Chromium: invio UI → backend upstream reale con Rust → Ollama simulato → testo visualizzato; conversazione presente dopo ricaricamento |
| Richiesta ricevuta dal simulatore | Modello configurato, prompt italiano, `think=false`, `num_ctx=4096`, `num_predict=512`, nessuno strumento |
| Errori browser e richieste esterne nel percorso chat provato | Nessuno osservato |
| Aggiornamento dei sorgenti | 4 test passati: verifica hash e modifiche locali, backup, rollback su errore, porta occupata e symlink |
| API reali e porta occupata | Modello cloud 400, modifica strumenti 403, origine esterna 403; launcher rifiuta una porta occupata senza fermare il server |
| Ollama reale e Mac Intel | **Da verificare**: installazione, qualità, latenza, arresto/riavvio e annullamento in HTTP reale |

Il simulatore restituisce testo e tempi sintetici: questi risultati non sono un benchmark del modello. Per la verifica browser si è usato Playwright/Chromium dopo che il daemon agent-browser non ha potuto aprire il socket nell'ambiente di prova. Non è stata eseguita l'intera suite upstream, che comprende numerose integrazioni non abilitate in questa fase.

Ripetizione dei controlli mirati dopo l'installazione delle dipendenze:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_andrea*.py' -v
cd frontend
npm exec --yes --package=npm@11.19.0 -- npm test -- src/lib/andrea-local.test.ts src/lib/chat-telemetry.test.ts
```

`tests/andrea_fixture_server.py` è un server di prova manuale con Ollama simulato, da eseguire nella venv con l'estensione Rust disponibile. Serve la UI già compilata, usa dati temporanei e la porta 8008; non avviarlo insieme al launcher sulla stessa porta. Non usare la sua risposta o i suoi tempi per valutare il modello.

## Integrazioni successive

1. Primo avvio e benchmark sul Mac, stesso modello e carico: tempo del primo testo, totale, correttezza e annullamento.
2. Collaudo Obsidian sul Mac con note reali: ricerca, lettura, estratti, stato delle note e qualità delle citazioni. Il collegamento e i controlli su dati sintetici sono già pronti; il riassunto richiede comunque verifica umana.
3. Memoria esplicita, consultabile e cancellabile. Migrazione tramite esportazione/importazione con schema e provenienza, senza copiare database tra schemi diversi.
4. Skill personali adattate e provate con casi sintetici, prima di autorizzare strumenti e radici di file.
5. Feedback sugli errori con valutazioni ripetibili; poi strumenti, scheduler e automazioni con permessi specifici. Salvare una lezione non dimostra che il modello l'abbia appresa o applicata.

## Modifiche alla sorgente

Nuovi file: launcher, `scripts/andrea/`, profilo e policy, test mirati e questa documentazione. Moduli frontend adattati: `App.tsx` (invito leaderboard), `api.ts` (origine locale e modello), `analytics.ts` e `supabase.ts` (servizi esterni disattivati), `sse.ts` (propagazione errori e chiusura lettore streaming). Nessuna modifica alla licenza o al codice Rust upstream.

Il fork è pubblico. Non committare conversazioni, credenziali, note, dati fiscali, email, database, audio o configurazioni personali.

## Note Obsidian: collegamento esplicito in sola lettura

Aprire **Data Sources** nella build locale: questa pagina mostra ora **Note Obsidian**, invece dell'ingestion upstream. Incollare il percorso completo della cartella e scegliere **Collega cartella in sola lettura**. Il percorso deve essere dentro la cartella utente e non può coincidere con l'intera cartella utente, usare risalite, cartelle nascoste o collegamenti simbolici. La configurazione è salvata solo in `~/.openjarvis-andrea/obsidian.json`, con permessi privati. **Scollega** rimuove il percorso dalla configurazione; non cancella alcuna nota. Non committare questo file.

La ricerca legge solo file `.md`, con corrispondenza per parole nel corpo, titolo e percorso. Le righe di frontmatter non diventano testo degli estratti. La lettura completa mostra il file originale come testo, senza eseguire HTML o script. Per gli estratti si riusa il parser di frontmatter upstream, limitandolo ai campi scalari di titolo e stato; i controlli di accesso, le righe originali e le esclusioni sono aggiunti dal fork. Nessun embedding o secondo modello viene scaricato.

Il pulsante **Riassumi gli estratti con Jarvis** esegue una nuova ricerca sul backend e invia al modello al massimo tre estratti di 900 caratteri, contrassegnati N1–N3. Bozze, note superate, stati sconosciuti/ambigui e note prive di contenuto sono escluse dal riassunto ma rimangono consultabili. Le note senza stato dichiarato sono ammesse se hanno un corpo utilizzabile: non significa che siano verificate o aggiornate. Titolo e stato restano etichette dichiarate dalle note.

Gli estratti visualizzati sotto la risposta sono gli stessi inseriti nel prompt, non una ricostruzione successiva. **Leggi nota aggiornata** apre il file attuale, che può essere diverso dallo snapshot. Citazioni mancanti o riferimenti a fonti non fornite producono un avviso; una citazione presente non dimostra che ogni affermazione sia corretta. La risposta del modello va confrontata con gli estratti. Il pannello non salva riassunti o fonti nelle note o nella memoria permanente; lasciare la pagina interrompe una generazione in corso.

Limiti iniziali: file da massimo 256 KiB, fino a 1000 note/8000 voci per ricerca e circa 8 MiB di contenuto. Il controllo del tempo di scansione è effettuato tra le letture dopo due secondi; non è un timeout del filesystem. La UI segnala ricerche parziali e file saltati, non dichiara di avere letto l'intero vault. Cache solo in memoria, aggiornata con device/inode/dimensione/mtime/ctime; eliminazioni e cambi di cartella non riusano risultati precedenti. Lettura tramite file descriptor con `O_NOFOLLOW`; collegamenti simbolici, hard link e file non regolari vengono rifiutati. I/O fuori dall'event loop, con accessi serializzati al vault.

Il profilo concede queste sole API dedicate attraverso il controllo Host/Origin locale; i permessi generici dei tool e i connettori automatici rimangono disattivati. Non è una sandbox del sistema operativo.

Collaudo sintetico aggiuntivo (Linux, backend upstream reale con estensione Rust, Ollama simulato): configurazione dalla UI, ricerca nel corpo senza summary/tag YAML, lettura raw con HTML inerte, fonti identiche nel prompt e nel pannello, esclusione di bozze/superate/vuote, aggiornamento del file senza alterare lo snapshot, cancellazione e nuova generazione, eliminazione, ricerca vuota, configurazione conservata dopo reload, scollegamento. Chromium 1440×1000 e 390×844: nessun errore JS, richiesta esterna o overflow orizzontale osservato. Simulatore avviabile con `tests/andrea_fixture_server.py --notes`; non usare il suo testo o i suoi tempi come misura dell'inferenza reale.

File aggiunti/adattati in questa fase: `scripts/andrea/vault.py`, `runtime.py`, `launch.py` (riserva della porta anche durante la preparazione), `frontend/src/pages/AndreaNotesPage.tsx`, `App.tsx` (pagina locale caricata su richiesta), `sse.ts` (evento fonti preservato tra chunk e errori espliciti), test vault/frontend e fixture. Licenza e codice Rust upstream invariati.

## Interpretazione del budget nell'interfaccia

Il campo `suggested_max_tokens` proviene dal classificatore di complessità upstream. Può indicare 1024 anche quando il runtime locale impone 512 all'engine, trasmesso a Ollama come `options.num_predict`. Il pannello lo etichetta `Suggested budget`: non rappresenta il limite effettivo o il numero di token generati.

## Aggiornamento mirato da un'installazione già funzionante

`scripts/andrea/update_notes.py` prepara un aggiornamento dei soli sorgenti di questa integrazione. Scarica i file da un commit fissato, verifica tutti gli SHA-256 prima di modificare il progetto e controlla i file principali contro la versione di partenza. Differenze locali inattese, file collegati o un server ancora in ascolto sulla porta 8008 interrompono l'operazione. Non termina processi.

Il backup dei sorgenti esistenti viene creato in `~/.openjarvis-andrea/update-backups/`. Un errore durante le sostituzioni ripristina i file già aggiornati; i nuovi file applicati sono rimossi nel rollback. `.env`, `.venv`, database, vault e altre configurazioni non vengono copiati o sostituiti. Le dipendenze e la compilazione sono gestite successivamente dal launcher esistente. Il collaudo dell'aggiornamento su macOS va confermato dall'utente prima di dichiararlo applicato al suo Mac.

## Correzioni del collaudo: ricerca e riassunti

La scansione ha un limite di 10 secondi, mantenendo gli altri limiti di file, byte e accesso. La scelta dell'estratto tokenizza ogni riga una sola volta e riusa gli insiemi di parole, preservando il criterio della finestra di quattro righe. Titolo e percorso hanno un peso maggiore nell'ordinamento.

Quando la richiesta corrisponde esattamente alle parole significative del titolo di una nota, il riassunto usa le fonti attive con quel titolo (massimo tre), anziché aggiungere menzioni incidentali da altri documenti. La ricerca continua a mostrare gli altri risultati. Questo è un riassunto mirato alla nota nominata, non un controllo di tutte le possibili contraddizioni nel vault. In assenza di titolo esatto si mantiene la selezione dei primi risultati utilizzabili.

Una ricerca parziale ora impedisce l'avvio dell'inferenza, con un errore visibile. Il prompt richiede citazioni per le singole affermazioni, conflitti espliciti, distinzione tra dati mancanti e zero, attribuzione delle date dichiarate e delle opinioni della fonte. La data di modifica del file non stabilisce quale fatto sia vero o attuale. Queste istruzioni non costituiscono un validatore della correttezza del modello.

Validazione di questa correzione: 13 test mirati dell'adattatore, con dati sintetici e il parser scalare upstream eseguito isolatamente. Comprendono sei regressioni nuove su titolo esatto, fonti con lo stesso titolo ma dati discordanti, rifiuto di scansioni parziali prima dell'inferenza e numero di tokenizzazioni con righe lunghe. Nessun Ollama reale o backend Rust completo utilizzato in questa esecuzione; nessuna modifica frontend. La qualità delle nuove risposte e la latenza complessiva restano da collaudare sul Mac.


## Misure locali e collaudo riproducibile

Il middleware locale registra soltanto metadati delle ultime 50 richieste in RAM; il riavvio li cancella. GET /api/andrea/metrics rispetta il medesimo controllo di Host/Origin. Non vengono scritti log con query, messaggi, estratti, percorsi delle note o risposte. Il modello, gli identificativi casuali, le durate, il conteggio dei chunk e l'usage upstream sono i soli dati della generazione conservati.

RequestMeasurement usa perf_counter. firstTextMs parte dall'ingresso nel middleware fino al primo contenuto non vuoto passato a ASGI send; generationFirstTextMs parte dall'invocazione dell'applicazione upstream. Le durate generationMs includono il percorso upstream e l'invio dello stream, non sono tempi esclusivi di calcolo Ollama. retrievalMs include costruzione degli estratti per il riassunto; la precedente ricerca visualizzata nella UI è una richiesta separata. totalMs copre questa richiesta nel backend. Queste misure non certificano il primo testo dipinto dal browser, né la qualità della risposta.

Il parser di osservazione ricompone frame SSE spezzati, ignora fonti/ruoli/contenuto vuoto, separa completamento, troncamento, errore, timeout e annullamento. Il conteggio dei chunk non viene presentato come numero di token. Le quantità usage sono quelle riportate dal server upstream e possono includere stime. I tempi di caricamento e valutazione del prompt di Ollama non vengono ricostruiti dal primo chunk: in questo percorso upstream non sono disponibili nelle risposte SSE e restano una futura integrazione.

scripts/andrea/collaudo.py usa soltanto 127.0.0.1:8008 e il modello già configurato. Richiede OpenJarvis acceso. Non cambia il vault, non installa modelli e non ne forza l'espulsione dalla memoria, non cambia configurazione e non scrive report automaticamente.

- Modalità quality: sei casi sintetici con il medesimo prompt dei riassunti di produzione. Non legge il vault. Stampa risposte, criteri, tempi e controlli formali; ogni qualityVerdict resta pending_review. Nessun confronto di parole certifica il significato. I casi coprono dato esplicito, dato non verificato nelle note, conflitto, evento passato risolto, opinione estranea e assenza della risposta. Lo stato delle note e la ricerca parziale restano verificati dai test dell'adattatore, che controllano l'esclusione e il mancato avvio dell'inferenza.
- Modalità timings: tre ripetizioni per chat breve e riassunto sulle note (sei richieste; massimo dieci ripetizioni per percorso). La query predefinita è kpi self publishing, modificabile con --notes-query. Le risposte e gli estratti vengono scartati: l'output conserva soltanto identificativi delle fonti e misure. Stato freddo/caldo non determinato; nessun p95 ricavato da questo campione. La mediana usa solo richieste con stato completed, che indica conclusione del protocollo, non accuratezza.

I tempi firstTextClientMs e totalClientMs riguardano il client di controllo nel Terminale, non il browser. Il collegamento alla misura backend usa l'header x-openjarvis-request-id. I due orologi misurano durate separatamente e non vengono sottratti tra loro.

Validazione di questa modifica: 8 test su misure, protocollo ASGI e privacy; 3 test sul client e sulla separazione dei verdetti; 13 regressioni dell'adattatore con parser upstream isolato e dati sintetici. Il backend Rust completo, il modello reale e il browser non sono stati eseguiti per questa modifica. Nessuna modifica frontend; nessuna nuova dipendenza. La sintassi Python e il caricamento dei casi JSON sono verificati. Qualità del modello e latenza reale restano da misurare sul Mac.


## Domande con presupposti falsi e ripetizione di un solo caso

Il collaudo reale dei sei casi sintetici ha rilevato una risposta contraddittoria nel caso historical: il modello ha presentato un problema come ancora aperto e subito dopo come risolto, benché la fonte documentasse soltanto la risoluzione. La suite di accuratezza non è superata. I controlli formali di citazioni e completamento erano positivi: non costituiscono una verifica del significato.

Il prompt condiviso precisa ora che la domanda non è una fonte di fatti e può contenere un presupposto falso. Un problema documentato come risolto non va dichiarato ancora aperto senza evidenza di riapertura; la conclusione va limitata agli estratti. Questa istruzione è una correzione mirata da verificare con il modello reale, non una garanzia di correttezza né un addestramento.

collaudo.py quality --case historical raccoglie soltanto quel caso usando i medesimi estratti e criteri già fissati. Senza --case rimangono i sei casi originali. La selezione è disponibile solo per quality. Nessun criterio è stato cambiato dopo la risposta. Dopo una modifica al prompt globale, il controllo del caso fallito non sostituisce la verifica degli altri cinque prima di dichiarare superata la suite.

Il test del manifest dell'aggiornamento precedente verifica la struttura e la versione di partenza, anziché confrontare i sorgenti attuali con hash appartenenti a un commit precedente. Gli hash dei download restano verificati dall'aggiornatore e dalla rilettura al commit pubblicato.

## Conteggi espliciti e protezione dai conflitti

Il collaudo completo documentato in quality-review-2026-10-01.md resta negativo per la versione precedente: citazioni formalmente corrette non hanno impedito una negazione del conflitto e una parafrasi non sostenuta dalla fonte.

scripts/andrea/evidence.py aggiunge un percorso limitato per domande semplici sui titoli/libri pubblicati e sulle copie vendute. Riconosce solo campi espliciti e valori interi, compresi gli alias dichiarati nel modulo. Copia le righe originali con le citazioni: date, periodi e marketplace restano nella citazione e non vengono ricostruiti da modifiedAt. Valori differenti vengono mostrati insieme senza scegliere, sommare o supporre che la separazione delle schede risolva il problema. Periodo e ambito devono essere chiariti: valori di periodi diversi possono essere entrambi validi.

Dati mancanti, stime, frazioni, valori scalati, negazioni, metriche sconosciute e domande operative restano fuori da questo percorso. Non è un verificatore generale della semantica né delle fonti esterne. Le altre richieste continuano a usare il prompt e il modello già configurati; le loro sintesi restano da verificare. Il controllo non addestra il modello e non prova che un fatto dichiarato dalla nota sia vero.

Per le domande quantitative gestite il testo di una trascrizione privo di un campo pertinente non viene aggiunto alla risposta. Non si applica una percentuale minima di parole coincidenti per certificare l'accuratezza. La selezione delle fonti nel vault, le esclusioni per stato e il rifiuto di una scansione parziale sono conservati.

Il raccoglitore quality ora attraversa lo stesso percorso backend delle risposte sulle note, con notes_sources contenente soltanto i tre estratti sintetici già pubblicati. Non legge il vault e non cambia i sei estratti o i criteri. notes_sources è un ingresso locale limitato, protetto da Host/Origin e validazione delle dimensioni; non ammette percorsi di file o stati arbitrari. L'origine provided è distinta da vault. I casi explicit, conflict e opinion possono usare il percorso dei campi espliciti; gli altri continuano a interrogare il modello. Un esito futuro della suite verifica il sistema completo, non dimostra che il modello da solo abbia corretto i propri errori.

L'evento local_sources e le misure distinguono answerMode explicit_fields/model_synthesis e inferenceUsed. Se il modello non viene invocato, generationMs e generationFirstTextMs rimangono null. La velocità di una risposta estratta non va presentata come un miglioramento della velocità di Ollama. Nessun testo delle note o della risposta viene aggiunto allo storico delle misure.

L'interfaccia conserva i riferimenti e la lettura delle note, ma evita di affermare che ogni risposta abbia usato il modello. Le sole modifiche frontend sono quattro testi; nessuna modifica a Suggested budget, al modello, ai limiti di generazione, alla memoria o alle dipendenze.

Validazione originaria: 41 verifiche mirate riuscite sul campo di applicazione, ASGI, misure, client, aggiornamento e adattatore con parser scalare upstream isolato. Il backend Rust completo non è stato eseguito nella checkout parziale. Sul Mac sono poi confermati l'installazione, la build frontend in 1,55 secondi e i sei casi sintetici del sistema, revisionati come corretti. Il controllo successivo nel browser ha mostrato un limite distinto nella selezione delle fonti di una domanda naturale; è documentato in quality-review-2026-10-01.md e affrontato nella sezione seguente.

## Titoli delle note dentro le domande

Una domanda naturale può nominare una nota, per esempio chiedere il conteggio riportato nei KPI di una specifica attività. Il conteggio delle parole nel corpo di note lunghe faceva salire trascrizioni e rinvii prima della nota richiesta. Il solo caso di ricerca uguale al titolo non copriva questa domanda.

named_paths riconosce titoli completi come sequenze ordinate di parole, ignorando articoli e preposizioni già dichiarati in STOP. I titoli con una sola parola richiedono una ricerca uguale al titolo. Un titolo breve contenuto in uno più lungo nominato non aggiunge una seconda fonte; menzioni separate di più titoli e copie con lo stesso titolo restano candidati. Non esistono percorsi o nomi di note personali fissati nel codice.

La ricerca dà precedenza ai titoli nominati prima di tagliare i primi dieci risultati. La risposta usa soltanto le fonti attive appartenenti a quel gruppo, massimo tre. Se il gruppo richiesto è escluso per stato o privo di contenuto, non viene sostituito silenziosamente da una trascrizione. Una ricerca generica mantiene la selezione per parole e più fonti. Questa è una regola lessicale con ambito dichiarato: non risolve sinonimi, titoli non nominati, negazioni complesse o tutti i conflitti della banca dati.

Il controllo dei campi riconosce anche la forma esplicita «I libri pubblicati sono **47**», copiandola per intero. Negazioni, stime e unità scalate restano escluse, anche dopo marcatori Markdown. Non vengono aggiunti numeri o informazioni mancanti alla nota.

Consultati tests/memory/test_retrieval_quality.py, tests/memory/test_bm25.py, tests/connectors/test_obsidian.py e src/openjarvis/tools/storage/bm25.py dell'upstream, commit c4da16e1ca3d21f4cc1905d4200063e564104f0f. Si mantengono il parser upstream già in uso e i controlli separati su ordinamento, fonte, limiti e risultati multipli. Il backend BM25 completo passa dal bridge Rust e pubblica eventi: non viene attivato insieme a ingestion, database o memoria automatica per correggere questo adattatore in sola lettura. Non si dichiara eseguita l'intera suite upstream.

La regressione è stata riprodotta prima della modifica con una nota sintetica e quindici trascrizioni. Dopo la correzione sono passati 21 controlli dell'adattatore, 12 delle evidenze, 8 delle misure, 3 del client e 6 dell'aggiornamento: 50 verifiche mirate. È coperto anche il percorso ASGI che legge file sintetici reali, seleziona la nota nominata e risponde dal conteggio senza chiamare il modello. Modello, prompt, budget, frontend e dati rimangono quelli precedenti. Restano da verificare sul Mac l'installazione di questa correzione, la precedenza della nota richiesta e la risposta nell'interfaccia sul vault effettivo.

scripts/andrea/update_retrieval.py applica cinque file fissati a un commit, verificando baseline e SHA-256, con la transazione di backup e rollback già usata. Richiede OpenJarvis fermo sulla porta 8008; non modifica note, database, profilo, dipendenze o il Jarvis originale.

## Procedura richiesta per ogni nuovo intervento

Prima di modificare codice, verificare lo stato del fork e consultare i test upstream pertinenti in https://github.com/open-jarvis/OpenJarvis/tree/main/tests. Fissare il riferimento esaminato e documentare cosa si recupera, cosa viene adattato e quali controlli non certificano il risultato richiesto. Non sostituire il collaudo locale con la semplice presenza di test upstream.

Per questo intervento sono stati letti tests/connectors/test_obsidian.py e tests/evals/scorers/test_doc_qa.py, al commit c4da16e1ca3d21f4cc1905d4200063e564104f0f. Si mantiene il parser Obsidian upstream e il modello di verifiche separate su contenuto, citazioni e protocollo. Lo scorer documentale controlla corrispondenze di parole e citazioni: non viene usato per dichiarare vere le affermazioni. I nuovi test coprono il controllo conservativo dei campi e il mancato avvio dell'inferenza quando non serve.


## Prossimi task e moduli futuri (2026-10-04)

La [roadmap dei moduli futuri](future-capabilities-roadmap.md) registra ricerca web, confronto Amazon con analisi del prodotto, recensioni, feedback del venditore e vendite dichiarate, controllo Mac e vocali WhatsApp. Sono funzionalità pianificate, non già attive. Quantità vendute non disponibili non vengono dedotte dal numero delle recensioni; nessuna reputazione è garantita da un punteggio. Acquisti e modifiche rilevanti richiedono revisione del risultato pronto.

La [raccolta delle fasi native nella stessa sintesi reale](production-native-phases.md) è conclusa e superata nell'ambito previsto sul Mac: installazione, sintesi della nota scelta riesaminata e frame finale della medesima richiesta disponibili. Osservati circa 5,84 s di caricamento, 14,99 s di valutazione del contesto e 20,36 s di produzione dei token; primo aggiornamento UI circa 41,27 s. Nessun miglioramento prestazionale dichiarato da un solo campione. Il successivo [confronto del riuso in produzione](production-native-phases.md#confronto-del-riuso-in-produzione-concluso-e-superato) è concluso e superato con una sola nuova generazione: 795 token di contesto dichiarati in cache su 796, caricamento 1,734 ms e valutazione del contesto 152,761 ms; produzione 19237,198 ms per 138 token. Sintesi riesaminata favorevolmente nel caso scelto. I tempi UI della ripetizione sono esclusi perché la scheda è stata osservata in secondo piano. Il confronto successivo di testi più concisi è ora concluso senza raggiungere le soglie fissate; candidata non adottata e produzione invariata.

## Confronto di testi più concisi concluso senza adozione (2026-10-04)

Il [confronto isolato di sintesi più concisa](concise-qualification-text-experiment-2026-10-04.md) ha completato le quattro richieste sintetiche sul Mac: nessun risparmio di token nel caso ordinario e più token nella candidata avversariale. La produzione dei token non migliora e il riferimento avversariale è rifiutato per unsupported_value_update. Soglie fissate prima della raccolta non superate, nessuna candidata adottata, nessuna modifica alla produzione. Misure pubblicate filtrate senza testi o storico personale. Le prove precedenti sul caso reale e sul riuso restano valide nel loro ambito, senza garanzie su altre sintesi.

Il [diagnostico successivo](qualification-rejection-diagnostic.md) prepara una sola nuova richiesta sul caso avversariale pubblico con i messaggi di produzione, conservando il JSON per analisi anche se rifiutato. Serve a identificare il predicato problematico; non è una ripetizione per promuovere l'esperimento fallito, non rilassa controlli e non legge il vault. Sei controlli nuovi e quindici regressioni passati in sviluppo. La singola diagnosi reale è ora conclusa: nessun rifiuto nel nuovo campione, JSON acquisito, ma causa del rifiuto precedente non risolta. La nuova frase omette il predicato di persistenza della fonte; formato accettato non significa equivalenza completa. Nessuna ulteriore ripetizione o modifica del server richiesta.

## Correzione della qualifica e della consultazione in corso

Il [collaudo Mac del prefisso](qualification-clause-fix.md#esito-reale-del-collaudo-mac) è concluso: pattern nativo e predicato/ambito conservati, ma qualità completa **fallita per omissione della consultazione con periodo, titolo e marketplace**. Nessuna adozione o riclassificazione del precedente fallimento prestazionale.

La [correzione della frase completa](qualification-sentence-fix.md) ha superato la singola prova sintetica Mac, anche nel confronto del significato: conserva tutta l'indicazione di consultazione e le quattro informazioni obbligatorie. F3 rimane letterale dalla fonte; gli altri tre record sono sintesi del modello. Esito circoscritto al caso osservato, senza apprendimento o verifica esterna. Il precedente prefisso incompleto resta una prova fallita.

La [integrazione Note Obsidian e l’aggiornamento a quattro file](qualification-sentence-production.md) sono installati e collaudati nel caso reale: compilazione completa sul Mac riuscita, trasporto concluso, controlli tecnici accettati e confronto manuale con i quattro fatti della nota favorevole. Conservati qualifica, ambito, indicazioni di consultazione e date distinte; origine letterale e origine del modello dichiarate. 148 controlli Python e 12 dell’interfaccia superati in sviluppo. Primo aggiornamento della risposta UI 45290 ms: qualità del caso superata, latenza ancora da ottimizzare. Nessun testo personale pubblicato; nessuna ulteriore prova necessaria per chiudere questo caso. Prossimo task: ridurre la latenza preservando gli stessi requisiti, senza riclassificare gli esperimenti precedenti falliti.
