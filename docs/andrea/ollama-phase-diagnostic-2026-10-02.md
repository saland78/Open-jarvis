# Diagnostica delle fasi Ollama — 2026-10-02

La baseline precedente è conclusa. Le prime attese elevate e i circa dieci
secondi delle sintesi non hanno ancora una causa determinata. Questo controllo
osserva tre nuove richieste, senza attribuire retroattivamente una causa alle vecchie.

Consultati su GitHub `src/openjarvis/engine/ollama.py`,
`tests/engine/test_ollama.py`, `tests/engine/test_ollama_runtime_options.py`
upstream e `src/openjarvis/server/routes.py` del fork alla baseline
6983426f2086484901f1efd3317f0132b504b075. Lo streaming upstream è già asincrono;
non viene riscritto. Il percorso non streaming conserva `engine_timing`, mentre
quello streaming non trasmette le durate native nella risposta testuale corrente.

`scripts/andrea/ollama_phases.py` invia tre richieste streaming sequenziali
direttamente a Ollama locale. Riutilizza la funzione `notes_messages` del runtime
pubblico verificato tramite SHA-256: vengono compilate soltanto le due assegnazioni
del prompt e questa funzione, senza importare o avviare il runtime. La domanda e
la fonte sintetiche coincidono con `notes_generated` della baseline; la rotta
OpenJarvis conserva il system prompt esplicitamente fornito. Modello Instruct,
temperature 0.4, contesto 4096, limite 512 e think false restano invariati.

Nessuna lettura del vault o dei profili privati; nessuna modifica al progetto,
stato, dipendenze o configurazione globale. Nessun unload, warm-up aggiuntivo,
opzione keep_alive o retry. Le richieste ordinarie possono comunque caricare il
modello e riutilizzare le cache, come qualsiasi inferenza. Non usare altre chat
contemporaneamente. Il processo non passa attraverso il limite di concorrenza del
server OpenJarvis: tenere l'applicazione accesa ma inattiva durante la serie.

Il frame finale Ollama espone durate in nanosecondi: total_duration,
load_duration, prompt_eval_duration ed eval_duration. Il rapporto converte in
millisecondi e conserva i contatori presenti; campi mancanti restano nulli.
Token/s deriva esclusivamente da eval_count ed eval_duration validi, mai dai
chunk. Non si sommano durate native ai tempi del client. `/api/ps` viene letto
prima/dopo ciascuna richiesta, conservando solo la presenza del modello scelto
e tre numeri: un modello presente non certifica cache calda o caricamento gratuito.
Proxy disabilitati e redirect rifiutati, chiamate limitate agli URL locali fissi.
Lettura limitata a 4 MiB, riga 256 KiB; timeout socket 90 s e verifica del tempo
trascorso fra letture. Il timeout socket non è una garanzia di interruzione
istantanea del calcolo Ollama. Testi generati, prompt, altri modelli e messaggi
d'errore non compaiono nel rapporto. Errori, EOF senza done e troncamenti restano
distinti; qualità semantica non valutata. Non viene ripetuta la serie per ottenere
tempi favorevoli.

È una diagnosi diretta del modello, non una misura end-to-end del browser/server,
né una comparazione perfettamente controllata con la precedente baseline.
Non forza uno stato freddo e non dimostra la causa delle precedenti attese.
La raccolta sul Mac resta da eseguire; non sono dichiarati miglioramenti.

Riferimenti primari: https://docs.ollama.com/api/chat e
https://docs.ollama.com/api/ps. Verifiche di sviluppo: protocollo finale,
conversione delle unità, dati mancanti, troncamento, errore, EOF, limiti,
versione del prompt, tre richieste senza retry e filtraggio dei dati privati.
Nove nuovi test e sei regressioni della baseline passati; il nuovo controllo
include tre richieste streaming HTTP effettive contro Ollama simulato, con
snapshot di sola lettura. Nessuna inferenza reale eseguita nel contenitore.
