# Sintesi strutturata nel profilo locale — 2026-10-02

La nuova modalità esplicita **Sintesi strutturata** riusa il contratto JSON e la copertura dei contesti datati collaudati nei quattro casi sintetici: tre risposte dell'esperimento precedente e una nuova risposta datata corretta. Quella revisione non era ancora un collaudo dell'integrazione: installazione e risposte attraverso il backend reale sul Mac restano da verificare.

## Comportamento

`notes_structured: true` richiede `notes_query` e non può essere combinato con `notes_brief: true`. Restano prioritari i conteggi diretti e la protezione letterale delle qualifiche datate. Chat, passaggi brevi, ricerca e sintesi libera conservano i rispettivi percorsi. Il prompt libero è invariato.

Il percorso generativo usa `sec.engine.stream_full`, passando `response_format={"type":"json_object"}`. Ollama riceve `format=json` solo quando richiesto esplicitamente. BudgetOllama continua a imporre modello configurato, contesto 4096, 512 token, temperatura 0.4, think=false e keep_alive=15m. Nessuno strumento, seconda inferenza, retry automatico, modello alternativo o servizio esterno.

Un solo stream viene accumulato entro 32000 caratteri e 4096 chunk, completato e validato prima di mostrare testo. Lo stream viene consumato fino alla fine, inclusa la scansione post-hoc del wrapper di sicurezza. JSON incompleto, troncamento, chiamate a strumenti, fonti sconosciute, date non presenti nei supporti o copertura incompleta dei contesti riconosciuti impediscono la visualizzazione delle affermazioni. Un elenco vuoto significa astensione. Contesti ambigui riconosciuti impediscono l'inferenza. Il risultato non viene trasformato da un secondo modello: il renderer aggiunge le citazioni e gli estratti originali restano visibili.

**Il validatore non prova l'implicazione semantica, la correttezza della fonte o lo stato esterno.** Può accettare una parafrasi semanticamente errata con formato, riferimenti e date corretti. Il testo e l'interfaccia richiedono esplicitamente il confronto con le fonti. Il vecchio fallimento della sintesi libera resta un fallimento; questa modalità non lo riclassifica e non garantisce ogni futura risposta.

## Misure e interruzione

`structuredFirstJsonMs` misura il primo frammento del modello dall'avvio della raccolta, non mostrato; `structuredGenerationMs` misura la raccolta completa; `structuredValidationMs` misura i controlli; `structuredAcceptedTextMs` misura dalla richiesta ASGI il testo accettato, presente soltanto se accettato. Il primo contenuto ASGI/browser può invece essere un messaggio di rifiuto. Non sommare orologi diversi.

`structuredOutcome` distingue accepted, rejected e abstained. `completed` resta un esito di trasporto, non di qualità. Le misure mantengono solo categorie e numeri in RAM, senza JSON generato, note, query, affermazioni o percorsi. Un disconnect cancella la raccolta e libera il vincolo di singola richiesta; non è una misura della rapidità con cui Ollama ferma il calcolo. Timeout ed errori non espongono il JSON parziale.

## Verifica di sviluppo

- Consultati su GitHub `tests/engine/test_ollama.py` e `tests/server/test_stream_bridge.py` upstream, inclusa la regressione che vieta una seconda inferenza per riscrivere il risultato.
- 102 test Python del profilo/ASGI e dei trasporti isolati passati, inclusi 13 nuovi controlli del percorso strutturato, sei casi della raccolta finita e forwarding JSON.
- 44 regressioni dei precedenti esperimenti passate: copertura 8, contratto 8, scope 6, thread 7, fasi Ollama 9 e baseline 6. I test storici usano una fixture pubblica del runtime originale; gli script standalone conservano i propri hash e rifiutano deliberatamente il nuovo runtime.
- 37 test frontend passati: callback e hook, proprietà delle richieste, interruzioni, privacy delle misure e rendering statico. Non costituiscono una prova di paint del browser reale.
- Typecheck e build Vite/PWA locali passati. TypeScript JavaScript 5.9.3 e Workbox development sono adattamenti del solo contenitore, non distribuiti. La build standard del Mac resta da verificare.
- Intera suite upstream e backend Rust completo non eseguiti in questo contenitore. Ollama reale e vault personale non disponibili qui.

## Collaudo Mac finito

Dopo aggiornamento e riavvio, `check_structured.py` invia sei richieste pubbliche sintetiche attraverso OpenJarvis: qualifiche datate, riapertura, opinione irrilevante, importo assente con istruzione nella fonte, problema storico e conteggi discordanti. Nessuna nota personale letta. Conserva risposte sintetiche solo per revisione umana nel risultato locale; elimina request ID e contenuti non selezionati dalle misure. `qualityVerdict=pending_review` non significa superato. Una protezione deterministica resta distinguibile dalla generazione del modello.

Poi verificare una risposta nella pagina Note Obsidian e il riquadro dei tempi. La fase sarà conclusa soltanto dopo questi risultati; non sono dichiarati miglioramenti di latenza o accuratezza universale. PR #1 sempre draft, nessun merge; Jarvis originale, note, profili, database e dipendenze non modificati.

## Aggiornamento verificato

`update_structured.py` installa 10 file sorgenti dal commit `f9555f0b76428e9ba424cada882b35a827fbedcf`, senza note, database, configurazioni o dipendenze. Richiede la porta 8008 libera, verifica gli hash di download e le sei baseline dei file esistenti, crea backup e ripristina i file già sostituiti in caso di errore. I quattro moduli/dati nuovi non possono sovrascrivere file locali diversi. SHA-256 dello script: `892259e659cb2a3c4659b1ddbff729b59290575071f5a61c7ac9b1262a071de6`.

Manifest reale verificato per applicazione, backup, sentinelle private sintetiche, ripetizione idempotente, rollback al terzo rimpiazzo, hash errato, baseline incompatibile e porta occupata. Tutti i 23 file del commit sorgenti riletti da GitHub e confrontati esattamente con quelli collaudati. Installazione Mac e i sei risultati reali restano da raccogliere.
