# Riuso del modello locale — 2026-10-02

La diagnosi diretta conclusa mostra: modello non presente prima della prima
richiesta, circa 4.83 s di caricamento e 7.65 s di preparazione contesto;
nelle successive il modello è presente, 566 token del prompt risultano letti
dalla cache e il primo testo arriva in circa 150 ms. La generazione resta circa
8.8 token/s. Sono osservazioni di quella serie, non una garanzia per ogni chat.

Consultati su GitHub engine Ollama e test engine/runtime_options upstream,
insieme al runtime del fork alla versione 16a6ecdf674561b5da7f3144810813d3680954e4.
Il client upstream riusa già connessioni asincrone. Non occorre riscrivere
streaming o memorizzare risposte. Il prompt stabile è già all'inizio dei messaggi;
non cambiamo ordine, contenuto, budget, modello o numero di richieste simultanee.

Modifica circoscritta: il BudgetOllama personale passa keep_alive="15m".
I tre metodi dell'engine (generate, stream e stream_full) trasmettono questa
opzione al livello superiore del payload Ollama, soltanto quando specificata.
Gli altri chiamanti senza opzione mantengono il comportamento precedente.
Ollama documenta un default di cinque minuti e il parametro per richiesta:
https://docs.ollama.com/faq e https://docs.ollama.com/api/chat.
Non viene modificato OLLAMA_KEEP_ALIVE o un servizio globale; il modello scelto
rimane comunque una risorsa del processo Ollama condiviso. Altri client o
pressione di memoria possono cambiare durata, cache o presenza del modello.

La scelta finita di 15 minuti limita i ricaricamenti dopo brevi pause e conserva
più a lungo la memoria occupata dal modello. La diagnosi riporta circa 3.18 GB
nel campo sizeBytes, non un inventario completo della memoria del processo.
Non promette maggiore velocità di generazione, memoria illimitata, contesto
sempre in cache o qualità universale. Nessun preload, heartbeat, inferenza
di riscaldamento, unload o modello diverso. La prima richiesta dopo un vero
scaricamento può ancora essere lenta. Il riuso della cache di inferenza non
equivale ad apprendimento o addestramento. Chiudere OpenJarvis non scarica subito
il modello da Ollama: scadrà secondo le regole di Ollama e le altre richieste.

Sei test nuovi verificano i payload effettivi dei tre metodi isolando soltanto
i trasporti/dependenze, omissione dell'opzione per altri chiamanti, valore 0,
parametri locali invariati e due richieste di controllo senza retry. Ottantadue
regressioni del profilo locale passate, inclusi citazioni, fonti, qualifiche e
misure. Il prompt di produzione è verificato identico tramite hash del runtime
dopo la rimozione della sola opzione aggiunta. Nessun benchmark Mac del nuovo
comportamento ancora eseguito e nessuna suite Rust/upstream completa dichiarata.

`check_reuse.py` riusa il client collaudo installato verificato via hash. Due
richieste notes_generated con gli stessi estratti sintetici della baseline;
nessun vault letto. Passano dal server reale, con limite di concorrenza e prompt
di produzione. Il rapporto conserva le risposte sintetiche per revisione umana,
tempi client/server filtrati e presenza/scadenza del solo modello scelto letta
da /api/ps. Le altre identità, timestamp assoluti e request ID sono scartati.
Scadenza relativa superiore a dieci minuti è un riscontro dell'opzione applicata,
non una prova che il modello sopravviva quindici minuti o che la cache sia
completamente riutilizzata. La scadenza usa l'orologio civile del Mac, separato
dalle durate monotone della risposta. Non si attende a vuoto per scaldare o
forzare un modello freddo, non si ripete la prova finché migliora.

Installazione prevista con script pin/hash, backup e rollback: quattro file
(engine, runtime, controllo sintetico e test); OpenJarvis deve essere fermo
sulla porta 8008. Note, frontend, profili, database, dipendenze e Jarvis originale
non vengono aggiornati. Il vecchio ollama_phases.py rifiuterà il runtime nuovo
per hash: è un controllo di versione deliberato, non un guasto dell'app.
I test della diagnosi conclusa usano quindi una fixture della versione pubblica
precedente, invece di pretendere che il runtime aggiornato abbia il vecchio hash.
Il manifest reale di update_reuse.py è verificato per applicazione e backup,
ripetizione idempotente, rollback al terzo rimpiazzo, download con hash errato,
baseline locale incompatibile e porta occupata. Profili, .env e sentinelle dei
dati conservati. Lo script scarica da un commit preciso e rifiuta modifiche locali
incompatibili prima di sovrascrivere i file.

Collaudo Mac da concludere: installazione, riavvio, due richieste complete sul
percorso model_synthesis con scadenza osservata, revisione delle due risposte
che non devono chiamare aperto il problema storico risolto. Timings generativi
variabili non bastano da soli a dichiarare un miglioramento. Nessuna conclusione
sulla precedente regressione della sintesi libera viene modificata.
