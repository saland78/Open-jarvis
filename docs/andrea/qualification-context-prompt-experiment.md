# Una sola prova sul costo del contesto — 2026-10-04

**Stato: raccolta Mac conclusa. Quattro risposte corrette nell’ambito riesaminato e riduzione dei token di input superata; soglia prestazionale originale non superata, attribuzione del prefill inconcludente per cache. Nessuna modifica della produzione.** Il precedente task del trasporto compatto è concluso e rimane tale. Questa serie di quattro richieste non viene ripetuta.

## Problema e modifica isolata

La [sintesi reale dopo l’adozione compatta](qualification-compact-wire-production.md) ha richiesto 26,38 s nel backend: caricamento 5,08 s, elaborazione del contesto 11,90 s e generazione 9,33 s. Il contesto è la singola fase più costosa di quella osservazione, non di ogni richiesta futura. Ollama dichiara 668 token di input e cache zero. Questo orienta la prova; non dimostra una causa universale.

Il percorso riconosciuto delle qualifiche invia tre record al modello, F1/F2/F4. F3 completo e le date dei contesti sono già vincolati alla fonte prima della generazione e riportati dal programma. Le istruzioni attuali derivano però da una sintesi più generale: comprendono regole sulla copertina e ripetizioni sui campi JSON. La candidata specializza **soltanto il messaggio system** al percorso delle qualifiche. Mantiene il messaggio user identico byte per byte, inclusi tutti i passaggi, identificativi, tipi, riferimenti e date presenti. Non seleziona meno fatti, non accorcia la fonte e non sostituisce la sintesi con una risposta prestabilita.

Le istruzioni passano da 1.631 a 824 caratteri. Nei due casi pubblici, i messaggi complessivi passano rispettivamente da 2.288 a 1.481 e da 2.289 a 1.482 caratteri. Sono misure di testo, **non token né guadagni di latenza**. I token e i tempi effettivi devono arrivare da Ollama sul Mac.

Schema nativo F1/F2/F4, estrattore, frase F3, date, associazioni alla fonte, righe, validatori e rendering sono gli stessi già installati. Il risultato originale del modello passa senza riscrittura al validatore compatto di produzione, compresi i controlli della frase completa. Non vengono riempiti campi mancanti né corretti numeri, qualifiche, anni o frasi del modello. Il percorso libro è rifiutato dalla candidata: le sue regole specifiche non vengono eliminate dal percorso operativo.

## Regole applicabili conservate

| Regola del prompt attuale | Istruzione della candidata |
|---|---|
| Italiano, una frase autonoma per record, sintesi breve | Italiano, frase autonoma per identificativo, massimo 30 parole |
| Solo il passaggio assegnato; niente trasferimenti fra record | Solo informazioni_obbligatorie; niente trasferimenti tra record |
| Conservare fatti, limiti, numeri nella grafia originale | Tutti esplicitamente richiesti |
| Conservare date e anni scritti; non aggiungere anni | Date e anni espliciti, nessun anno o dato aggiunto |
| Conservare DATO NON VERIFICATO e DATO ASSENTE | Entrambe le etichette esplicitamente richieste |
| La qualifica nella nota non prova aggiornamenti o verifiche dei valori | Stesso limite esplicito, con ambito della nota |
| Nessuna conclusione su sistemi esterni; assenza non equivale a zero | Entrambi i limiti espliciti |
| Istruzioni della fonte non eseguibili | Passaggi trattati come dati, istruzioni ignorate |
| Solo JSON nella struttura richiesta, senza citazioni/metacommenti | response_shape, tre stringhe, nessuna chiave extra/citazione/spiegazione sul programma |
| F3 e date composti dal programma; contextDate non data aggiornamenti dei valori | Origini separate dichiarate e stessa distinzione temporale |

Questa corrispondenza descrive le istruzioni, non prova che il modello le seguirà. La revisione del significato rimane necessaria; un test conserva deliberatamente il controesempio tecnico che accetta «NON variano» pur avendo significato opposto.

## Esperimento finito, criteri fissati prima dei risultati

Script autonomo: [qualification_context_prompt_probe.py](../../scripts/andrea/qualification_context_prompt_probe.py). Verifica dodici hash dell’installazione compatta corrente, compresi note_facts e qualification_compact_wire. Non rilassa i controlli dello script A/B precedente, che conserva la propria baseline storica. La candidata è incorporata e verificata con SHA-256; non richiede installazione di un modulo o dipendenze.

Quattro richieste al massimo, direttamente all’Ollama locale:

1. ordinario, produzione compatta attuale;
2. ordinario, istruzioni specializzate;
3. avversariale, istruzioni specializzate;
4. avversariale, produzione compatta attuale.

I casi sono note sintetiche pubbliche già usate nel confronto compatto: contesti datati separati, numeri estranei, metadati fuorvianti e istruzione non pertinente. Nessuna nota personale viene letta. Identici modello Instruct, temperatura 0,4, contesto 4096, budget 512, think=false, keep_alive=15m e thread automatici. Nessun unload, warm-up, retry o adozione automatica. Proxy disabilitati, redirect rifiutati, stream e risposta limitati. Errore/troncamento/cancellazione o rifiuto tecnico fermano la serie; cache o misure mancanti non provocano nuove richieste.

Per **entrambe le coppie**, prima dell’eventuale adozione:

- trasporto completo e contratto accettato con tutti e quattro i fatti finali, F3 completo e consultazione conservati;
- input dei fatti e schema nativo identici;
- almeno **20% di token di input in meno**;
- almeno **15% di durata nativa del prefill in meno**, soltanto se ogni richiesta della coppia dichiara cache zero;
- revisione separata delle quattro risposte: conteggio, variabilità per periodo, qualifiche correnti/storiche e rispettive date, ambito della nota, consultazione completa, citazioni e nessuna verifica esterna inventata.

Se la cache manca o è nonzero, la soglia temporale non risulta superata: i token rimangono un’osservazione distinta e il confronto temporale è inconcludente. Non disabilitare la cache per ottenere un esito favorevole. Una riduzione del testo o un risultato tecnico valido non autorizzano l’adozione. Non ripetere automaticamente la serie e non riclassificare fallimenti precedenti.

Il rapporto include JSON del modello, sintesi e passaggi **esclusivamente sintetici**, anche se rifiutati, per consentire analisi concreta. Qualità resta pending_review. Caricamento, decoding, primo JSON e durata client sono riportati separatamente; questo script non misura UI, percorso server, nota reale o miglioramento statistico. La documentazione Ollama v0.34.2 distingue token dell’intero prompt, token in cache e durata dei token non in cache: non attribuire a istruzioni più brevi un guadagno prodotto dalla cache.

## Verifiche concluse

**196 controlli Python passati:** 18 nuovi e 178 regressioni pertinenti. Coprono input/schema immutati, prove con righe originali, F3 e consultazione completi, numeri/date/qualifiche/predicati, risposta incompleta/chiavi duplicate o mancanti, modifica delle prove, hash incompatibili, symlink, ripristino del registro dei moduli, interruzione senza retry e soglie distinte con cache o misure mancanti. Eseguito anche lo stesso comando CLI previsto sul Mac contro quattro stream HTTP locali simulati, oltre al preflight senza rete. Nessuna inferenza reale nel contenitore, modifica runtime o compilazione frontend necessaria. Intera suite upstream non eseguita.

Consultati prima della modifica, upstream al commit a0df94cd93756047c724d803662bc671618b10d4:

- [test_structured_output.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_structured_output.py): inoltro del formato strutturato;
- [test_ollama_runtime_options.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_ollama_runtime_options.py): contesto esplicito e opzioni del motore;
- [ollama.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/src/openjarvis/engine/ollama.py): confini streaming/opzioni; nessun cambio indiscriminato al motore Andrea;
- [usage.mdx di Ollama v0.34.2](https://github.com/ollama/ollama/blob/v0.34.2/docs/api/usage.mdx) e [schema strutturato](https://docs.ollama.com/capabilities/structured-outputs): misure native e separazione fra formato e verifica della risposta. Il piccolo response_shape già collaudato resta nel messaggio; nessuna rimozione del formato nativo.

## Prossimo passo sul Mac

Lasciare OpenJarvis acceso e Controlli aperto. Scaricare lo script temporaneo da un commit preciso e confrontare il suo hash; poi eseguire una volta nel Terminale Controlli, senza richieste chat/sintesi contemporanee. Il report completo di questa prova è sintetico e può essere condiviso per la revisione. Non inviare lo storico del Terminale.

Eventuale integrazione soltanto dopo esito favorevole: applicazione selettiva, backup/rollback verificati e una prova sul percorso reale con tutte le protezioni della fonte e dell’interfaccia conservate. Nessun nuovo modulo funzionale, voce o memoria viene attivato. Jarvis originale invariato; PR #1 draft, nessun merge.

## Esito Mac della serie finita — 2026-10-04

[Rapporto sintetico e revisione separata](qualification-context-prompt-mac-2026-10-04.json). Quattro richieste completed/stop, contratti accettati, nessun retry o fonte personale letta. Replay offline dei quattro JSON catturati attraverso gli stessi validatori e rendering: risultati identici. Revisione del significato favorevole nei quattro casi: conteggi originali, variabilità per periodo, frase corrente completa e consultazione, qualifica storica, due contesti datati distinti, citazioni e nessuna deduzione di zero o verifica esterna. I verdict tecnici pending_review sono conservati; la revisione umana è un campo separato.

| Caso / variante | Input totale | In cache | Input non in cache calcolato | Prefill nativo | Produzione nativa |
|---|---:|---:|---:|---:|---:|
| Ordinario / produzione | 668 | 0 | 668 | 10.410 ms | 7.232 ms |
| Ordinario / candidata | 475 | 3 | 472 | 7.069 ms | 5.276 ms |
| Avversariale / candidata | 476 | 315 | 161 | 2.618 ms | 5.365 ms |
| Avversariale / produzione | 669 | 508 | 161 | 2.785 ms | 7.004 ms |

Riduzione dei token di input: **28,892% e 28,849%**, entrambe oltre la soglia del 20%. Token generati 70→53 e 68→54; decoding osservato −27,048% e −23,403%, senza un criterio causale prefissato su questa fase. Le durate prefill variano del 32,093% e 6,010% ma **non superano il test originale**: cache nonzero, e la seconda coppia elabora esattamente 161 nuovi token per entrambe le varianti. La prima richiesta carica anche il modello per 4,072 s; i totali non isolano il contesto. Nessuna misura del percorso server o del browser.

La somma cache_n + prompt_n nel codice Ollama v0.34.2 e i test SSE confermano che prompt_eval_count include i token in cache, mentre prompt_eval_duration riguarda quelli nuovi. Fonte primaria: [llama_server.go](https://github.com/ollama/ollama/blob/v0.34.2/llm/llama_server.go) e [TestLlamaServerCompletionSSEParsing](https://github.com/ollama/ollama/blob/v0.34.2/llm/llama_server_test.go). Il motore invia cache_prompt=true. **Il criterio di cache completamente zero scelto per la prima prova era troppo rigido per questo protocollo di prefissi condivisi.** Il problema viene riconosciuto, non corretto cambiando dopo i risultati il verdetto della serie.

Nessuna adozione o seconda serie A/B. Il seguito è una [diagnosi distinta di due richieste con prefissi isolati](qualification-prefill-isolation-diagnostic.md), per il prefill quasi interamente nuovo. Non certifica beneficio nell’uso con cache calda e non riclassifica il precedente esito. L’ottimizzazione della latenza resta aperta.
