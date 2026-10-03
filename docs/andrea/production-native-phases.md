# Fasi native Ollama nella sintesi di produzione

Stato al 2026-10-04 (Europe/Rome): modifica e verifiche di sviluppo pronte; installazione e controllo sul Mac ancora da eseguire. Nessun miglioramento di velocità dichiarato.

## Problema e comportamento

Il tempo strutturato osservato nel percorso della nota scelta comprende l'intera chiamata al motore, senza isolare caricamento, valutazione del prompt e produzione dei token. Le vecchie prove dirette di Ollama non spiegano retroattivamente una diversa richiesta di produzione.

L'engine rich streaming osserva ora il frame finale della stessa chiamata Ollama tramite un callback interno opzionale. Il BudgetOllama locale collega il callback alla singola sintesi strutturata tramite ContextVar; il collector task eredita il contesto e lo resetta anche su errore, timeout e cancellazione. Nessuna seconda richiesta, warm-up, retry aggiuntivo, preload o unload.

Gli altri chiamanti senza observer conservano payload e stream precedenti. L'eventuale retry upstream senza tools resta invariato; gli strumenti continuano a essere esclusi dal profilo locale. Il callback non viene serializzato nel payload Ollama e un errore di osservazione non altera la generazione.

Le misure vengono aggiunte come ollamaNative al record numerico già in RAM. L'osservatore mantiene soltanto durate e contatori interi non negativi dichiarati dal frame done=true; nessun contenuto, path, timestamp, risposta o frame originale viene conservato. Dati mancanti o invalidi rimangono null, mentre zero dichiarato rimane zero. Nessun dato ereditato da una richiesta precedente.

## Confini delle misure

| Campo | Significato |
|---|---|
| terminalFrameReceived | Frame finale nativo ricevuto; non certifica qualità o stop |
| loadMs | Durata di caricamento dichiarata da Ollama |
| promptEvalMs | Durata di valutazione del contesto dichiarata da Ollama |
| evalMs | Durata di produzione dei token dichiarata da Ollama |
| totalMs | Totale nativo dichiarato da Ollama; distinto dal totale ASGI/browser |
| promptEvalCount, promptEvalCachedCount | Contatori nativi, quando presenti; non stime upstream |
| evalCount, evalTokensPerSecond | Token nativi prodotti e rapporto fra evalCount ed eval_duration, se valido |

Durate native convertite da nanosecondi in millisecondi. Il rapporto token/s usa la durata nativa originale, non il valore arrotondato. Non sommare orologi diversi o chiamare un residuo una particolare fase. Una durata di caricamento non certifica da sola lo stato della cache. Primo frammento JSON e primo testo accettato restano misure distinte.

Prompt, schema, conteggi, qualifiche, date, citazioni, validatore, ricerca, modello Instruct e parametri di inferenza restano invariati. Nessuna modifica frontend o dipendenza. La validità tecnica della sintesi resta distinta dalla sua revisione semantica.

## Verifica di sviluppo

61 controlli mirati passati: 13 nuovi e 48 regressioni del budget/retention, percorso reale ASGI delle note, sintesi strutturata, misure e prompt qualifiche. Confrontato lo stesso trasporto ricco con/senza observer: stesso payload e stessi chunk. Controllati schema nativo e budget, nessuna richiesta aggiuntiva, frame incompleto/troncato, errore del callback, isolamento fra task e cancellazione. Sul collector ASGI con dati sintetici, stessa risposta con/senza raccolta numerica.

I trasporti sono simulati usando i metodi di produzione; nessuna inferenza reale o nota personale letta. Non eseguiti intera suite upstream, backend Rust completo, browser reale o collaudo sul Mac per questa modifica. Compilazione sintattica dei quattro file runtime riuscita. Il lettore delle misure esegue un solo GET locale, con proxy e redirect disabilitati, lettura limitata e output filtrato senza ID, modello o testo privato.

Consultati nuovamente [OllamaEngine upstream](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/engine/ollama.py) e [test Ollama upstream](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_ollama.py), oltre alle regressioni già presenti nel fork. La consultazione non equivale alla loro esecuzione. Significato e unità dei campi verificati nella [documentazione API Ollama](https://docs.ollama.com/api/usage) e [chat](https://docs.ollama.com/api/chat).

## Installazione e verifica Mac finite

Un installer separato scaricherà quattro sorgenti da un commit preciso, con hash, verifica della baseline, porta 8008 libera, backup e rollback. Non modifica note, configurazioni, database, dipendenze o Jarvis originale. Non eseguire con il server acceso.

Dopo installazione e riavvio:

1. Nella pagina Note Obsidian, aprire la stessa nota scelta già collaudata e chiedere una sola sintesi strutturata della nota. Non ripetere la ricerca globale o i sei casi sintetici.
2. Confrontare la risposta con i passaggi originali e verificare che date e qualifiche rimangano separate. Completamento/accettazione del contratto non certificano il significato.
3. In Controlli eseguire scripts/andrea/read_native_phases.py con il Python del progetto, lasciando OpenJarvis in esecuzione. Il lettore non legge il vault e non genera altre risposte.
4. Verificare che il record più recente della sintesi abbia un frame finale e durate native; eventuali campi assenti rimangono null. La selezione è dichiaratamente l'ultima sintesi strutturata in memoria, non un benchmark di un'altra richiesta.

Criterio di chiusura: misure della stessa richiesta disponibili e confronto semantico favorevole nell'ambito della nota scelta. In caso di errore raccogliere l'esito e risolverne la causa, senza ripetizioni per ottenere un campione favorevole. Una sola osservazione non dimostra un miglioramento prestazionale; serve per scegliere il successivo intervento misurato. Nessuna dashboard esterna verificata.

La [roadmap dei moduli futuri](future-capabilities-roadmap.md) conserva ricerca web, Amazon, controllo Mac e voce/WhatsApp come task successivi. PR sempre draft senza merge.
