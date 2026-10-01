# OpenJarvis personale: chat e note locali separate

Repository: https://github.com/saland78/Open-jarvis

Sorgente: https://github.com/open-jarvis/OpenJarvis, commit `c4da16e1ca3d21f4cc1905d4200063e564104f0f` (1 ottobre 2026). Il fork conserva storia, licenza Apache-2.0 e relazione upstream. `main` conserva la base; queste modifiche sono su `feature/andrea-local-profile`, PR draft #1. Il precedente Jarvis rimane in un'altra repository e cartella.

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
