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

## Raccolta Mac conclusa

Script scaricato dal commit 6378bc3e965fa4ab25f92d0d7e0f29a3e8dd4dc3,
hash verificato 7d05d314f14196886bc2666271b2457a9a1880cd6b6aab5c2c1e57d6dd35f2f9.
Il rapporto allegato è stato estratto senza pubblicare lo storico del Terminale.
Tre richieste completed/stop, nessun retry, qualità not_assessed. Controllati
ordine, tempi e calcolo token/s; pubblicato soltanto lo schema numerico consentito
in `ollama-phase-diagnostic-mac-2026-10-02.json`.

| Prova | Primo testo client (ms) | Totale client (ms) | Caricamento nativo (ms) | Preparazione contesto nativa (ms) | Generazione nativa (ms) | Token generati | Token/s |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 12503.063 | 22210.953 | 4827.501 | 7649.505 | 9707.271 | 86 | 8.859 |
| 2 | 149.751 | 9938.353 | 1.919 | 116.429 | 9788.905 | 86 | 8.785 |
| 3 | 151.702 | 10890.652 | 2.048 | 117.381 | 10739.167 | 95 | 8.846 |

Prima della prova 1 `/api/ps` non elencava il modello scelto; dopo la prova e
prima/dopo le altre risultava presente, contesto 4096, sizeBytes 3184001022,
sizeVramBytes 0. Questi numeri non identificano da soli hardware impiegato,
pressione di memoria, swap o un'impossibilità di accelerazione.

Ollama riporta prompt_eval_count 567 in ciascuna prova e
prompt_eval_cached_count rispettivamente 0, 566, 566. La preparazione del contesto
scende da 7649.505 ms a 116.429/117.381 ms con il riuso osservato; il caricamento
scende da 4827.501 ms a circa 2 ms. Nella prima prova la somma delle due durate
native è 12477.006 ms, prossima al primo contenuto client 12503.063 ms: questi
dati spiegano la gran parte dell'attesa iniziale di questa richiesta. Sono
orologi e confini diversi, non un'identità esatta o una misura del browser.

Nelle due successive il primo contenuto arriva in circa 150 ms e oltre il 98%
del tempo totale nativo è eval_duration. Il collo di bottiglia osservato dopo
il primo testo è dunque la generazione di 86/95 token, circa 8.8 token/s.
La terza risposta contiene più token pur usando la stessa richiesta: temperatura
invariata 0.4, nessuna uguaglianza del testo o qualità semantica attestata.
Non trasformare questi risultati in una spiegazione certa delle precedenti
prove, né in una misura end-to-end o in un miglioramento già applicato.

Consultati nuovamente su GitHub engine Ollama e test runtime_options upstream
durante la chiusura. Nessuna modifica al runtime Mac, al modello o ai parametri,
nessuna nuova serie necessaria per chiudere questa diagnosi. La fase è completata.
Direzione successiva: valutare riuso di modello e contesto sul percorso reale;
eventuali riduzioni delle risposte devono conservare i controlli di qualità
e non riproporre come risolta la precedente regressione del prompt breve.
