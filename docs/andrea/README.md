# OpenJarvis personale: prima chat locale separata

Repository: https://github.com/saland78/Open-jarvis

Sorgente: https://github.com/open-jarvis/OpenJarvis, commit `c4da16e1ca3d21f4cc1905d4200063e564104f0f` (1 ottobre 2026). Il fork conserva storia, licenza Apache-2.0 e relazione upstream. `main` conserva la base; queste modifiche sono su `feature/andrea-local-profile`, PR draft #1. Il precedente Jarvis rimane in un'altra repository e cartella.

## Prima versione

`Avvia-OpenJarvis.command` prepara un ambiente Python nel progetto, compila l'estensione Rust e l'interfaccia quando le sorgenti cambiano, quindi avvia la chat su **http://127.0.0.1:8008**. Il browser si apre dopo il controllo di salute del backend. Lascia aperto quel Terminale; Control+C ferma OpenJarvis. Un'altra istanza sulla stessa porta produce un messaggio e non viene terminata.

Il profilo usa esclusivamente Ollama a `127.0.0.1:11434`, con `qwen3:4b-instruct-2507-q4_K_M`, italiano, temperatura 0,4, contesto 4096 e massimo 512 token di risposta. Il backend impone questi limiti anche se le impostazioni del client o la classificazione della complessità upstream suggeriscono altri valori. La lista dell'interfaccia mostra soltanto il modello configurato, se installato. Nessun fallback cloud viene costruito.

Dati e cache di compilazione sono in `~/.openjarvis-andrea`, distinti dai dati del precedente Jarvis. L'avvio non importa il vecchio `.env`, i database, le skill o le note Obsidian. L'ambiente runtime non eredita credenziali cloud o altre configurazioni OpenJarvis. Le conversazioni della UI sono conservate dal browser per questa origine; ciò non costituisce apprendimento del modello.

Questa fase abilita **chat di testo**, con streaming, timeout di 90 secondi e una generazione per volta. Le altre richieste di modifica vengono rifiutate; gli strumenti hanno una policy esplicita senza concessioni e con deny globale. Memoria automatica, scheduler, canali, apprendimento, skill discovery e connettori restano disattivati. Il codice completo upstream rimane disponibile per le integrazioni successive. I relativi menu originali possono essere ancora visibili: la loro presenza non indica che la funzione sia già attiva.

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
| Test runtime | 7 passati: ambiente, origine, policy delle richieste, budget, concorrenza, timeout e cancellazione |
| Test frontend | 5 passati: URL locali, analytics, leaderboard, modello configurato e errore streaming |
| Chat nel browser | Chromium: invio UI → backend upstream reale con Rust → Ollama simulato → testo visualizzato; conversazione presente dopo ricaricamento |
| Richiesta ricevuta dal simulatore | Modello configurato, prompt italiano, `think=false`, `num_ctx=4096`, `num_predict=512`, nessuno strumento |
| Errori browser e richieste esterne nel percorso chat provato | Nessuno osservato |
| API reali e porta occupata | Modello cloud 400, modifica strumenti 403, origine esterna 403; launcher rifiuta una porta occupata senza fermare il server |
| Ollama reale e Mac Intel | **Da verificare**: installazione, qualità, latenza, arresto/riavvio e annullamento in HTTP reale |

Il simulatore restituisce testo e tempi sintetici: questi risultati non sono un benchmark del modello. Per la verifica browser si è usato Playwright/Chromium dopo che il daemon agent-browser non ha potuto aprire il socket nell'ambiente di prova. Non è stata eseguita l'intera suite upstream, che comprende numerose integrazioni non abilitate in questa fase.

Ripetizione dei controlli mirati dopo l'installazione delle dipendenze:

```bash
.venv/bin/python -m unittest discover -s tests -p test_andrea_local.py -v
cd frontend
npm exec --yes --package=npm@11.19.0 -- npm test -- src/lib/andrea-local.test.ts
```

`tests/andrea_fixture_server.py` è un server di prova manuale con Ollama simulato, da eseguire nella venv con l'estensione Rust disponibile. Serve la UI già compilata, usa dati temporanei e la porta 8008; non avviarlo insieme al launcher sulla stessa porta. Non usare la sua risposta o i suoi tempi per valutare il modello.

## Integrazioni successive

1. Primo avvio e benchmark sul Mac, stesso modello e carico: tempo del primo testo, totale, correttezza e annullamento.
2. Obsidian in sola lettura: estratti dal corpo, citazioni con percorsi/righe, stato delle note, aggiornamenti ed eliminazioni. Il connettore upstream va confrontato con i controlli già sviluppati nell'altro Jarvis.
3. Memoria esplicita, consultabile e cancellabile. Migrazione tramite esportazione/importazione con schema e provenienza, senza copiare database tra schemi diversi.
4. Skill personali adattate e provate con casi sintetici, prima di autorizzare strumenti e radici di file.
5. Feedback sugli errori con valutazioni ripetibili; poi strumenti, scheduler e automazioni con permessi specifici. Salvare una lezione non dimostra che il modello l'abbia appresa o applicata.

## Modifiche alla sorgente

Nuovi file: launcher, `scripts/andrea/`, profilo e policy, test mirati e questa documentazione. Moduli frontend adattati: `App.tsx` (invito leaderboard), `api.ts` (origine locale e modello), `analytics.ts` e `supabase.ts` (servizi esterni disattivati), `sse.ts` (propagazione errori e chiusura lettore streaming). Nessuna modifica alla licenza o al codice Rust upstream.

Il fork è pubblico. Non committare conversazioni, credenziali, note, dati fiscali, email, database, audio o configurazioni personali.
