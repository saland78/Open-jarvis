# Fasi native Ollama nella sintesi di produzione

Stato al 2026-10-04 (Europe/Rome): installazione e collaudo finito sul Mac conclusi e superati nell'ambito della nota scelta. Fasi native della stessa richiesta disponibili; nessun miglioramento di velocità dichiarato.

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

L'installer [update_native_phases.py](../../scripts/andrea/update_native_phases.py) scarica quattro sorgenti dal commit 80dca1e4b367bf026f229f59af5f39bfcaf39b3a, con hash, verifica della baseline, porta 8008 libera, backup e rollback. SHA-256 dello script: 5afeafed2f9b6c271f1a8b5493beb75041fe6e16a0364d85cebbbfa6e025d422. Non modifica note, configurazioni, database, dipendenze o Jarvis originale. Non eseguire con il server acceso.

Dieci test della transazione reale a quattro file passati: backup/sentinelle/permessi/ripetizione, hash errato, file incompatibile o mancante, rollback al terzo e quarto rimpiazzo, porta occupata, symlink, guardie e modifiche concorrenti, sintassi non valida e manifest preciso. Dieci regressioni dell'installer precedente passate usando fixture storiche esatte per runtime ed engine; i suoi hash non sono stati rilassati. Totale di questo task: 81 controlli mirati passati. Sorgenti e distribuzione pubblicati riletti per verificarne l'identità.

Dopo installazione e riavvio:

1. Nella pagina Note Obsidian, aprire la stessa nota scelta già collaudata e chiedere una sola sintesi strutturata della nota. Non ripetere la ricerca globale o i sei casi sintetici.
2. Confrontare la risposta con i passaggi originali e verificare che date e qualifiche rimangano separate. Completamento/accettazione del contratto non certificano il significato.
3. In Controlli eseguire scripts/andrea/read_native_phases.py con il Python del progetto, lasciando OpenJarvis in esecuzione. Il lettore non legge il vault e non genera altre risposte.
4. Verificare che il record più recente della sintesi abbia un frame finale e durate native; eventuali campi assenti rimangono null. La selezione è dichiaratamente l'ultima sintesi strutturata in memoria, non un benchmark di un'altra richiesta.

Criterio di chiusura: misure della stessa richiesta disponibili e confronto semantico favorevole nell'ambito della nota scelta. In caso di errore raccogliere l'esito e risolverne la causa, senza ripetizioni per ottenere un campione favorevole. Una sola osservazione non dimostra un miglioramento prestazionale; serve per scegliere il successivo intervento misurato. Nessuna dashboard esterna verificata.

La [roadmap dei moduli futuri](future-capabilities-roadmap.md) conserva ricerca web, Amazon, controllo Mac e voce/WhatsApp come task successivi. PR sempre draft senza merge.

## Esito Mac del 2026-10-04: concluso e superato nell'ambito previsto

Installazione verificata dell'installer distribuito al commit a86efaf84746978effee48964b72e25fe5d78fcc, hash dello script corrispondente e quattro file applicati con backup. Riavvio del launcher riuscito. Una sola sintesi della nota scelta nella pagina Note Obsidian, senza ripetizioni per ottenere un campione favorevole.

Trasporto completed e contratto accepted. Confronto umano della risposta visualizzata con i passaggi originali: favorevole per i quattro fatti selezionati. Conteggio dichiarato e variabilità per periodo conservati; qualifica aggiornata non verificata nella nota e assenza nella fotografia storica tenute separate con le rispettive date. Nessuna deduzione di zero, nessun report esterno dichiarato inesistente o mai scaricato, nessuna verifica esterna inventata. Questo esito riguarda quel caso, non una certificazione semantica universale o una verifica della dashboard.

Il lettore ha eseguito zero inferenze e nessuna lettura del vault. Il record più recente della sintesi strutturata ha terminalFrameReceived=true e tutti i contatori/durate attesi. L'output del lettore non valuta la qualità: il verdetto semantico deriva dal confronto separato nel browser. Numeri filtrati disponibili in [production-native-phases-mac-2026-10-04.json](production-native-phases-mac-2026-10-04.json), senza storico del Terminale, screenshot, testo, percorsi delle note, identificativi o dati personali.

| Fase della stessa richiesta | Durata |
|---|---:|
| Recupero nel backend | 2,71 ms |
| Caricamento nativo Ollama | 5835,091 ms |
| Valutazione nativa del contesto | 14992,081 ms |
| Produzione nativa dei token | 20364,808 ms |
| Totale nativo Ollama | 41231,624 ms |
| Primo frammento JSON nel backend, non mostrato | 20890,32 ms |
| Intero percorso di generazione nel backend | 41254,74 ms |
| Controlli del JSON | 3,15 ms |
| Primo testo accettato nel backend | 41262,95 ms |
| Totale della richiesta nel backend | 41263,37 ms |
| Primo aggiornamento della risposta nella UI | 41268 ms |

Contatori dichiarati da Ollama: promptEvalCount=796, promptEvalCachedCount=0, evalCount=138, evalTokensPerSecond=6,776. Il caricamento osservato non identifica da solo la causa o certifica lo stato iniziale della memoria. Lo zero riguarda il contatore di cache dichiarato per questa richiesta: non prova che il riuso sia impossibile. Nessun GET aggiuntivo dello stato Ollama è stato raccolto per questa osservazione.

Il costo principale di questa osservazione è nel motore: valutazione del contesto e produzione dei token, con un contributo di caricamento. Recupero e validazione hanno costi millisecondi. Il primo JSON non è testo accettato: la sintesi protetta viene mostrata dopo il completamento e i controlli. Non sommare i tempi del browser e del backend, né attribuire differenze fra orologi a una fase specifica. Una singola osservazione non dimostra un miglioramento rispetto a campioni precedenti.

Criterio di chiusura soddisfatto: misure native disponibili dalla medesima richiesta e revisione semantica favorevole nel caso scelto. Non sono necessarie altre generazioni per chiudere questo aggiornamento.

## Successivo intervento misurato

Prima di modificare nuovamente prompt o parametri, verificare il riuso del modello e del contesto sul percorso reale della nota scelta: keep_alive=15m è già configurato, ma questa osservazione contiene caricamento e nessun token dichiarato in cache. La vecchia prova sintetica diretta non sostituisce una misura del percorso di produzione.

Preparare un confronto finito con la stessa nota e il medesimo prompt, schema e modello, senza forzare unload, riscaldamenti aggiuntivi o retry. Conservare ogni esito e confrontare separatamente le fasi native e i medesimi criteri semantici. Se la cache non viene riusata, individuare le differenze del payload prima di proporre una modifica; non assumere che aumentare la retention acceleri il calcolo dei token. Nessuna modifica al runtime o nuovo benchmark è stato eseguito per registrare questo esito.

Per la chiusura e la scelta del prossimo task consultati nuovamente [test_ollama.py](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/tests/engine/test_ollama.py), [test_ollama_runtime_options.py](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/tests/engine/test_ollama_runtime_options.py) e il motore upstream allo stesso commit. Il percorso rich streaming è già asincrono: renderlo nuovamente asincrono non è la soluzione dedotta da queste misure. Consultazione distinta dall'esecuzione; nessuna nuova suite richiesta per questo aggiornamento di documentazione. Branch di lavoro verificato prima della modifica, PR #1 draft e non unita.

## Confronto del riuso in produzione: concluso e superato

Raccolta del 2026-10-04 sul Mac: una sola nuova sintesi della stessa nota e gli stessi quattro fatti supportati. Nessuna modifica a runtime, prompt, schema, modello o parametri; nessun warm-up forzato, unload o retry. La configurazione keep_alive=15m era già installata. Il lettore ha eseguito zero inferenze e non ha letto il vault.

La richiesta è completed/accepted. Il confronto separato della nuova risposta con i passaggi originali è favorevole: conteggio e variabilità conservati, qualifica corrente nella nota separata dall'assenza storica, date e riferimenti mantenuti, nessuno zero o stato esterno inventato. Il formato accepted non è stato usato da solo per certificare il significato. Verdetto circoscritto ai fatti selezionati, nessuna verifica esterna o certificazione universale.

| Misura | Prima osservazione | Unica nuova richiesta |
|---|---:|---:|
| Caricamento nativo | 5835,091 ms | 1,734 ms |
| Valutazione nativa del contesto | 14992,081 ms | 152,761 ms |
| Produzione nativa dei token | 20364,808 ms | 19237,198 ms |
| Totale nativo | 41231,624 ms | 19424,954 ms |
| Primo frammento JSON nel backend, non mostrato | 20890,32 ms | 191,11 ms |
| Primo testo accettato nel backend | 41262,95 ms | 19432,85 ms |
| Totale nel backend | 41263,37 ms | 19433,17 ms |
| Token di contesto dichiarati | 796 | 796 |
| Token di contesto dichiarati in cache | 0 | 795 |
| Token prodotti | 138 | 138 |
| Token/s nativi | 6,776 | 7,174 |

Ollama dichiara il riuso del contesto nella seconda richiesta. Il contatore cache e la riduzione dei costi di caricamento/valutazione verificano il riuso in questo caso; non sono una garanzia di permanenza in memoria dopo pause lunghe o altre richieste al modello condiviso. L'identità dei passaggi è stata confrontata nel browser, non dedotta dal solo numero di token.

La seconda prova è marcata dalla UI come osservata in secondo piano: i suoi tempi browser/UI sono esclusi dal confronto della latenza dell'interfaccia. Le misure del backend e le fasi native della medesima richiesta rimangono disponibili. Non occorre una nuova generazione per ricavare un campione UI favorevole: questo task riguarda il riuso osservato nel motore.

Il primo JSON in circa 191 ms non è una risposta verificata o visibile dopo 191 ms. Il testo viene mostrato soltanto dopo che la sintesi completa passa i controlli. Rimangono circa 19,24 s di produzione dei token; retrievalMs=1,69 e structuredValidationMs=1,97 non sono i costi dominanti. Le variazioni di token/s fra questi due campioni non dimostrano una modifica causale della velocità: il runtime è invariato, e il campione è finito.

[Numeri filtrati](production-native-reuse-mac-2026-10-04.json) senza risposte, note, percorsi, screenshot o storico del Terminale. Criterio soddisfatto e confronto chiuso: nessun'altra generazione richiesta per questo task.

## Prossimo candidato: meno token con gli stessi fatti

Valutare una forma più concisa dei soli testi generati per i quattro fatti supportati, mantenendo tutti i fatti obbligatori, le qualifiche con ambito nella nota, le date, le citazioni, gli originali mostrati e l'intero validatore. Limitare la candidata al percorso riconosciuto delle qualifiche datate; il prompt dei libri e la sintesi generale rimangono separati. Nessuna adozione senza confronto finito di qualità e misure native; token ridotti non equivalgono a qualità migliore. Non ridurre il tetto di 512 token per provocare troncamenti e non mostrare JSON parziale privo di controlli.

Il [precedente esperimento sui thread](thread-generation-experiment-2026-10-02.md) è già concluso: quattro e otto thread hanno entrambe mediane token/s inferiori alla scelta automatica e non soddisfano la soglia stabilita. Conservare l'automatismo; non ripetere quell'esperimento per cercare un esito favorevole. Riusare gli esiti già acquisiti evita un nuovo ciclo di tentativi.

Questo candidato è soltanto il prossimo task: nessun prompt, codice runtime, dipendenza o configurazione è stato modificato per chiudere il confronto. Stato del branch e PR draft verificati, test engine/runtime_options upstream già consultati per il task al commit 792131feb3948aca0b54a94e0344f6827ff3129d; consultazione distinta dall'esecuzione. Jarvis originale e note intatti.
