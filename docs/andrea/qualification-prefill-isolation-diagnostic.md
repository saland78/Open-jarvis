# Diagnosi distinta: prefill con prefissi isolati — 2026-10-04

**Preparata e verificata in sviluppo, raccolta Mac ancora da eseguire. Non installata in produzione.** La [serie precedente](qualification-context-prompt-experiment.md#esito-mac-della-serie-finita--2026-10-04) conserva il proprio esito: informazioni e riduzione di input favorevoli, soglia prestazionale originale non superata. Non si ripetono i quattro campioni o si allentano i controlli delle risposte.

## Causa da isolare

Con riuso del prefisso, un prompt completo più corto può richiedere lo stesso numero di nuovi token: nel confronto avversariale precedente erano 161 per entrambe le varianti. La durata prefill non misura l’elaborazione di tutto il prompt completo. Ollama v0.34.2 attiva cache_prompt=true e riporta separatamente il conto dei token in cache. Nessuna scelta globale di cache, unload o warm-up va introdotta nel processo condiviso per questo collaudo.

La nuova domanda è circoscritta: **quanto cambia il prefill quando quasi tutto il contesto deve essere elaborato di nuovo?** Non si certifica l’uso quotidiano con cache calda, un ordine di grandezza della latenza UI o una velocità universale.

## Protocollo e criteri prima della raccolta

[qualification_prefill_isolation_probe.py](../../scripts/andrea/qualification_prefill_isolation_probe.py) è autonomo, temporaneo, con gli stessi dodici hash dell’installazione corrente. La candidata incorporata, estrattori, validator, schema nativo, fonte sintetica e parametri Ollama sono identici a quelli della prova precedente. Cambia soltanto il metodo di isolamento dei prefissi nelle richieste diagnostiche.

**Due richieste al massimo**, sul medesimo caso ordinario pubblico: produzione compatta, poi candidata con istruzioni specializzate. All’inizio del messaggio system si aggiunge un identificativo tecnico sintetico diverso per ciascuna richiesta, con una frase che lo esclude dai fatti da riportare. Le prime lettere dei due identificativi sono differenti; il resto è casuale e non contiene dati dell’utente. Non si modifica il messaggio user, alcun passaggio, la frase F3, date, budget, modello, opzioni, validatori o rendering. Gli identificativi servono a evitare il riuso delle istruzioni e non vengono adottati nel prompt di produzione.

Il riuso di una piccola intestazione del formato chat può rimanere. Non si presume che sia eliminato: la **copertura nativa effettiva** deve soddisfare entrambi i limiti in ciascuna richiesta:

- non più di **8 token in cache**;
- almeno **98% del prompt non in cache**.

Questi sono limiti operativi prefissati per questa diagnosi, non una garanzia del tokenizer o la nuova interpretazione del vecchio test. Contatori mancanti, booleani, non interi, negativi, incoerenti o fuori limite rendono la misura non qualificata. Il conto dei nuovi token è prompt_eval_count − prompt_eval_cached_count, mai una stima dai caratteri.

Esito prestazionale favorevole soltanto con entrambe le richieste complete, quattro fatti accettati, consultazione completa, fonti e schema invariati, copertura qualificata, **almeno 20% di token non in cache e 15% di durata prefill in meno**. Le due risposte richiedono revisione separata sul significato; i quattro risultati sintetici precedenti restano conservati. Un passaggio tecnico o un tempo migliore non autorizzano l’adozione.

Nessun retry, sostituzione di una richiesta fallita, terzo campione, unload o warm-up. Non modificare file, profilo o database e non leggere il vault. Qualità, prestazione nativa, trasporto e misure UI rimangono esiti distinti. Il conteggio delle inferenze aggiuntive è esattamente quello tentato, massimo due. L’ordine unico ha limiti di campionamento; nessuna significatività statistica o beneficio sul totale viene dedotto.

## Verifiche e riferimenti

11 nuovi controlli passati: prefisso dichiarato e diverso senza alterazione dei fatti, stessi parametri e schema, contatori nativi coerenti, entrambi i vincoli della cache, soglie non superabili con metriche mancanti, interruzione senza retry, e stesso comando CLI del Mac contro due stream HTTP locali simulati con un piccolo prefisso in cache. Il replay offline di tutti e quattro i JSON Mac precedenti conserva risposte e fallimento della soglia originale. La dimostrazione di una risposta tecnicamente valida ma semanticamente opposta rimane pending_review.

Consultati nuovamente OpenJarvis al commit a0df94cd93756047c724d803662bc671618b10d4: [test_ollama_runtime_options.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_ollama_runtime_options.py), [test_structured_output.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_structured_output.py). Per i contatori: [Ollama v0.34.2 llama_server.go](https://github.com/ollama/ollama/blob/v0.34.2/llm/llama_server.go), [test SSE](https://github.com/ollama/ollama/blob/v0.34.2/llm/llama_server_test.go) e [Usage](https://docs.ollama.com/api/usage). Sorgenti consultati, non intere suite upstream eseguite. Nessuna inferenza reale nel contenitore.

## Passaggio Mac

Lasciare **OpenJarvis acceso**. Nel Terminale **Controlli**, scaricare da un commit preciso e verificare l’hash. Poi una sola esecuzione, senza chat/sintesi contemporanee. Condividere soltanto l’output sintetico della prova, senza lo storico del Terminale.

Produzione invariata, nessun installer o riavvio. Eventuale adozione richiede ancora regressioni dei confini di produzione e una sintesi reale con revisione dei fatti selezionati. Nessuna voce, memoria, automazione o modifica al Jarvis originale. PR #1 draft, non unire.
