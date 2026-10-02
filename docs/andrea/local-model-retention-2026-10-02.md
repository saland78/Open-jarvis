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
dopo la rimozione della sola opzione aggiunta. Il collaudo Mac circoscritto è
registrato sotto; nessuna suite Rust/upstream completa dichiarata.

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

## Collaudo Mac concluso e superato nell'ambito previsto

Script update_reuse.py scaricato dalla versione
b931ffe86a9117a5f33140f5210f93994705f196; hash verificato
01c5a42f29895ffa0375035a2eda52b80a98c45a4793eb406fead235ab277351.
Primo download interrotto da timeout di connessione, nessuna installazione;
secondo download riuscito e verificato prima dell'esecuzione. Quattro file
scaricati/verificati, backup creato, aggiornamento completato. Riavvio confermato
dal log finale; il KeyboardInterrupt precedente segue Control+C.

check_reuse.py ha effettuato due richieste complete sul percorso model_synthesis,
senza retry né lettura del vault. Rapporto filtrato in
`local-model-retention-mac-2026-10-02.json`: niente storico Terminale, percorsi
personali, risposte o request ID pubblicati. Consultato nuovamente il test
runtime_options upstream su GitHub durante la revisione.

| Prova | Modello caricato prima | Primo testo client (ms) | Totale client (ms) | Primo testo ASGI (ms) | Totale ASGI (ms) | Scadenza restante dopo (s) |
|---|---|---:|---:|---:|---:|---:|
| 1 | no | 13108.83 | 23416.12 | 13092.60 | 23400.72 | 899.98 |
| 2 | sì | 175.15 | 10820.84 | 173.46 | 10820.13 | 899.98 |

La seconda richiesta vedeva già una scadenza restante di 899.97 s prima della
generazione; dopo la risposta tornava a 899.98 s. Questa osservazione e i test
dei payload supportano l'applicazione della richiesta keep_alive=15m nel
percorso effettivo. Non è stato atteso un periodo inattivo di sei/quindici minuti:
retentionSurvivalAfterIdle resta not_tested. Scadenza relativa e tempi ASGI/client
sono osservazioni distinte, non si sommano. Il browser non è misurato qui.

Revisione umana dei due testi sintetici: entrambi descrivono il problema del
codice a barre come risolto, attribuiscono la copertina corretta alla data della
fonte e precisano che negli estratti non risultano problemi successivi o ancora
aperti. Non ripetono il difetto di definire ancora aperto il problema storico.
Esito passato soltanto per questo caso. Le frasi iniziali non contengono il
qualificatore "negli estratti", esplicitato subito dopo: non certificano lo stato
reale esterno. Il rapporto automatico conserva pending_review; il rapporto
filtrato aggiunge separatamente l'esito della revisione umana circoscritta.

Non è dimostrato un miglioramento causale rispetto alla precedente baseline:
due prove ravvicinate non testano l'effetto di una pausa lunga, e la prima
rimane lenta con modello non presente. Questa raccolta non misura le durate
native delle singole fasi, né i token/s; le precedenti osservazioni restano
separate. I circa dieci secondi necessari a completare la seconda risposta
non sono stati eliminati. Timings generativi variabili non bastano da soli a
dichiarare un miglioramento. Nessuna conclusione sulla precedente regressione
della sintesi libera viene modificata. Nessun ulteriore test richiesto per
chiudere questo collaudo circoscritto; PR sempre draft senza merge.
