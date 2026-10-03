# Confronto finito dei thread di generazione — 2026-10-02

Il prossimo intervento mira al tempo di generazione, rimasto circa 8.8 token/s
nella diagnosi conclusa. Prima di cambiare il profilo occorre verificare una
possibile leva CPU. Non sono cambiati modello predefinito, prompt o runtime.

Consultati su GitHub OpenJarvis engine Ollama e
tests/engine/test_ollama_runtime_options.py; fork verificato alla versione
2161955f173a7dbd0429b3ff52603181b234eb18, PR draft. Consultati anche i sorgenti
Ollama **v0.34.2**, corrispondente alla versione dichiarata sul Mac:
api/types.go (blob c83f3f2228e482fc3e4313b814317bd0c94d533f) espone NumThread,
default 0 per lasciare decidere al runtime; llm/llama_server.go
(blob 7a0b1ed334b348356268a70b5e1a48fe2c36e9fd) passa -t soltanto per valori
positivi espliciti. La presenza dell'opzione è verificata nel codice della
versione, non dedotta da suggerimenti di forum o variabili globali.

`thread_benchmark.py` riusa il codice della diagnostica locale già conclusa,
con hash del runtime aggiornato f47e5094a0a884ea6d250e99a5643403d4ecd332560abcd3a3af05cd0340c8b9.
Vengono compilate soltanto le definizioni del prompt pubblico e notes_messages,
senza importare il runtime. Stessa domanda e stesso estratto sintetico della
baseline; nessuna nota o configurazione privata letta. Modello Instruct,
temperatura 0.4, think false, contesto 4096, massimo 512 e keep_alive 15m.
L'unica differenza sperimentale è options.num_thread: omesso/4/8.

Nove richieste, esattamente tre per impostazione. Ordine prefissato:
automatico, 4, 8; 8, automatico, 4; 4, 8, automatico.
L'ultima usa il default automatico. Nessun retry, preload, unload, heartbeat
o riscrittura di file; il motore può ricaricare il modello e perdere la cache
quando cambia l'impostazione. È un effetto operativo della prova sul modello
del processo Ollama condiviso, non una modifica globale persistente. Non usare
altre chat o client contemporaneamente. Se si interrompe la serie, o se l'ultima
richiesta fallisce, non è attestato il ritorno al default nel processo già
caricato: la successiva richiesta ordinaria di OpenJarvis specifica di nuovo
le sue opzioni standard. Non terminare altri processi per forzare condizioni.

Confronto primario: mediana eval_count / eval_duration dei tre campioni completi
di ogni gruppo. Le durate native distinguono caricamento/preparazione/generazione;
totale e primo testo sono conservati, ma non provano un effetto di throughput
quando cambiano caricamento e cache. Numero di token variabile registrato,
nessuna conversione di chunk in token. Una risposta troncata/EOF/errore o senza
contatori validi resta esclusa e visibile, senza nuova prova. Le risposte
sintetiche sono conservate nel rapporto per revisione umana; nessun request ID
o altro modello registrato. Stessi limiti di 4 MiB complessivi, riga 256 KiB e
timeout socket 90 s con controllo della durata fra letture; risposta testuale
limitata a 32000 caratteri. Proxy disattivati e redirect rifiutati.

Soglia pratica stabilita prima della raccolta: almeno +15% sulla mediana della
scelta automatica, tutti e tre i campioni della candidata e del riferimento
validi. È soltanto un criterio esplorativo per passare alla revisione di
qualità, non significatività statistica o prova di causalità. Tre campioni non
controllano temperatura CPU, carico del Mac o tutte le variazioni. Il benchmark
non certifica i thread effettivi impiegati leggendo un semplice payload e non
misura il browser o il percorso server. Anche se la soglia passa, decisione
sempre not_adopted_requires_quality_review_and_server_validation.

Prima di adottare una candidata occorrono revisione delle risposte sintetiche,
controlli sui casi di conflitto/date/assenza di dati e verifica nel percorso
OpenJarvis. Se non emerge un guadagno utile, chiudere la prova senza cambiare
il profilo né ripetere finché i numeri diventano favorevoli. Ridurre la lunghezza
del prompt dopo la precedente regressione non è incluso in questo esperimento.

Verifica di sviluppo: sette test passati, inclusa una serie di nove richieste
streaming HTTP contro Ollama simulato; payload, ordine finito, default finale,
mediane e soglia, errori senza retry, contatori mancanti, EOF/troncamento e
limiti controllati. Nessuna inferenza reale eseguita nel contenitore.
Raccolta Mac conclusa: risultati e decisione riportati sotto.
Script autonomo temporaneo: non richiede installazione o arresto OpenJarvis.

## Raccolta Mac conclusa: nessuna candidata adottata

Nove richieste completed/stop, tre per impostazione, nessuna esclusione o
ripetizione. Ultima richiesta automatica completata. Confronto ricalcolato dai
contatori nativi e verificato sull'ordine prefissato.

| Impostazione richiesta | Campioni validi | Mediana token/s | Differenza rispetto ad automatico |
|---|---:|---:|---:|
| Automatico (opzione omessa) | 3 | 7.509 | riferimento |
| 4 thread | 3 | 6.983 | -7.00% |
| 8 thread | 3 | 6.793 | -9.54% |

Nessuna alternativa raggiunge la soglia esplorativa del +15%; entrambe sono
più lente in questa serie. **Esperimento concluso, scelta automatica mantenuta.**
Nessuna modifica a runtime, profilo, prompt o modello; keep_alive=15m conservato.
Non servono ulteriori ripetizioni per decidere sull'adozione di queste candidate.

Le richieste consecutive con la stessa impostazione (4 e 7) indicano 566 token
in cache e primo testo rispettivamente 196.236 e 170.207 ms. Le altre indicano
cache zero e caricamenti nell'ordine di 4.8–5.6 s: primo testo e totale non vanno
interpretati come solo throughput di generazione. Non sono misurati carico o
temperatura del Mac, né verificati i thread effettivi; non si attribuisce una
causa alla differenza rispetto alle serie precedenti. Questa prova diretta
non misura rendering browser o latenza dell'intero percorso OpenJarvis.

Revisione delle nove risposte sintetiche: tutte riconoscono la risoluzione
storica e indicano l'assenza di problemi successivi negli estratti. Restano
formulazioni da rendere più circoscritte: in particolare il campione 4 conclude
con un'affermazione generale senza citazione, dopo un contesto qualificato.
L'assenza di documentazione non prova l'assenza di problemi reali. Nessuna
certificazione universale della sintesi libera; il precedente esito negativo
non viene riclassificato. Il mancato guadagno basta a scartare entrambe le
candidate, senza ulteriore installazione o collaudo del server.

[Numeri filtrati della raccolta](thread-generation-experiment-mac-2026-10-02.json):
nessuno storico del Terminale, risposta, nota personale o request ID pubblicato.
Consultato nuovamente il test runtime_options upstream prima della chiusura.
PR #1 sempre aperta e draft, senza merge.
