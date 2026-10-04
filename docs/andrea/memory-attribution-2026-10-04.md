# Attribuzione del ricordo all'utente — difetto aperto

Il primo richiamo sintetico della memoria sul Mac ha recuperato il colore corretto, ma ha usato una formulazione in prima persona che assegnava la scelta a Jarvis. Il richiamo successivo alla correzione ha usato il nuovo colore con una formulazione corretta; non risolve retroattivamente il primo esito. Persistenza dopo riavvio ed eliminazione della voce confermate. Dopo l'eliminazione, in una nuova chat il modello dichiara di non avere l'informazione e non ripropone i colori precedenti.

## Diagnosi e candidato

Prima di preparare il candidato sono stati verificati branch e PR #1 al commit `e2289f6199b7be064bf5d5ac5eaa51ca2563d9ad`, ancora draft e non unita. Riletti [test MemoryService upstream](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/memory/test_memory_service.py), relativo servizio e [test del trasporto Ollama](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_ollama.py). Il test `test_extracted_facts_reach_model_context_end_to_end` verifica che i fatti raggiungano il contesto: non certifica l'attribuzione semantica nella risposta del modello. L'estrazione automatica resta disattivata.

Nel profilo attuale la policy accompagna il JSON con provenienza dichiarata, limiti di fiducia e assenza di autorizzazioni per azioni. Non esplicita il riferimento della prima persona nella domanda e nel ricordo. È una lacuna coerente con il difetto; non è una causa provata fino al confronto con il modello reale.

Il candidato aggiunge istruzioni che distinguono assistente, utente dichiarante e persone nominate. La prima persona dell'utente non diventa la voce dell'assistente; i soggetti terzi non vengono sostituiti con l'utente. Nessuna sostituzione automatica dei pronomi nella risposta, nessun nuovo strumento, dato esterno o addestramento.

## Tre richieste finite prima dell'adozione

`scripts/andrea/check_memory_attribution.py` verifica gli hash dei tre componenti installati: formatter della memoria, runtime locale e client del collaudo. Usa il formatter reale con voci sintetiche in RAM e aggiunge la policy candidata nel messaggio inviato alle tre richieste. Il processo del server non viene modificato; il candidato non è installato. La memoria personale deve essere vuota e la revisione stabile prima, durante e dopo la serie. Il controllo dello stato non pubblica voci, ID o revisioni private.

| Caso | Criterio semantico |
|---|---|
| Scelta dell'utente, formulazione impersonale | Colore corretto attribuito all'utente, provenienza dichiarata, nessuna scelta propria dell'assistente |
| Dichiarazione salvata in prima persona | Prima persona riferita all'utente, senza appropriazione da parte dell'assistente |
| Scelta di una terza persona, scelta dell'utente mancante | Non attribuire il colore della terza persona all'utente; dichiarare l'informazione mancante |

Tre richieste attraverso la chat di produzione a Ollama locale, senza retry automatici, lettura del vault, scrittura di memoria, modifica di opzioni del modello o chiamate di giudizio. Proxy e redirect disabilitati. Gli esiti falliti e le risposte troncate restano nel rapporto; se lo stato cambia, le richieste restanti non partono e i risultati precedenti sono conservati. Le risposte sintetiche richiedono lettura: `qualityVerdict=pending_review` anche con trasporto completato. Nessuna certificazione per parole chiave o riscrittura successiva della risposta.

Verifiche di sviluppo: sette nuovi controlli su consegna ASGI, conservazione dei soggetti letterali, stato vuoto e revisione, raccolta senza retry, conservazione dei fallimenti e rifiuto dei redirect; quindici test del modulo memoria e sette del suo installer precedente. **29 esecuzioni superate**, con motore simulato e senza inferenza reale. Frontend, archivio della memoria, runtime e percorso delle note invariati: nessuna nuova build necessaria per eseguire il diagnostico.

## Esito Mac del candidato con sola policy: negativo

Tre richieste completate, nessun retry, memoria vuota e revisione invariata. Revisione delle risposte: scelta dell'utente nella formulazione impersonale superata; **dichiarazione salvata in prima persona fallita**, perché la risposta mantiene la prima persona senza attribuzione; scelta della terza persona superata, con informazione dell'utente dichiarata mancante. `qualityVerdict=pending_review` del raccoglitore non è un giudizio positivo: questa lettura assegna due casi superati e uno fallito. Il candidato non è stato installato.

| Caso | Esito semantico | Primo testo client | Totale client |
|---|---|---:|---:|
| Scelta utente | Superato nel caso osservato | 10104,49 ms | 13589,87 ms |
| Prima persona salvata | Fallito | 977,31 ms | 2572,69 ms |
| Terza persona distinta | Superato nel caso osservato | 1157,35 ms | 8856,17 ms |

Sono osservazioni del client di controllo, non rendering browser né un confronto prestazionale. Stato caldo/freddo e causa della variabilità non determinati. Nessuno storico del Terminale, testo personale, screenshot o ID di richieste pubblicato.

## Diagnosi dell'integrazione e candidato con ruoli separati

Riletti [context.py upstream](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/src/openjarvis/tools/storage/context.py), [test_context.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/memory/test_context.py) e [routes.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/src/openjarvis/server/routes.py). `_ensure_identity_prompt` considera un messaggio system privo di metadata `memory_context` come grounding fornito dal chiamante: non aggiunge l'identità del server. Il modulo locale passa la memoria come system nel JSON della chat senza quel metadata; il suo testo comprende sia istruzioni sia dichiarazioni letterali dell'utente. Di conseguenza il prompt system del profilo non viene aggiunto nel normale ramo engine. Questa conseguenza del codice è verificabile; non prova da sola la causa semantica dell'errore. Il primo candidato aggiungeva già una distinzione esplicita assistente/utente, ma ha fallito comunque.

`check_memory_attribution_roles.py` prepara un secondo candidato: conserva il `system_prompt` del profilo pubblico locale verificato e le stesse istruzioni, mentre il JSON letterale dei ricordi diventa un messaggio **user** esplicitamente indicato come dichiarazioni salvate, dati e non autorizzazioni. Segue la domanda originale dell'utente. Un solo system iniziale, nessuna risposta assistant fittizia e nessuna riscrittura dei pronomi o del testo salvato. Non viene affermato che questo sia il meccanismo upstream: è un adattamento circoscritto del confine locale.

I tre casi, domande e criteri sono caricati dal precedente diagnostico verificato byte per byte; sono immutati. Gli hash di formatter, runtime e client sono ricontrollati, e il profilo deve corrispondere a quello pubblicato. Un profilo modificato interrompe la prova senza sostituirlo o pubblicarlo. Tutti gli altri vincoli del primo esperimento restano attivi: memoria vuota e stabile, tre richieste, nessun retry, nessuna installazione o scrittura, proxy e redirect rifiutati, esiti precedenti conservati.

Sei nuovi controlli tecnici verificano il candidato effettivamente consegnato al confine ASGI, la conservazione dell'identità del profilo, il JSON e i soggetti letterali, l'assenza di mutazioni dei payload e dei file, il rifiuto di baseline/profilo diversi e la raccolta con gli stessi criteri. Insieme alle 29 regressioni precedenti: **35 esecuzioni superate**, con motore simulato. Nessuna certificazione semantica del modello reale.

**Collaudo del secondo candidato sul Mac ancora da eseguire.** Nessuna correzione installata o qualità già dichiarata superata. Se tutti e tre i criteri passano, preparare l'aggiornamento dell'integrazione con backup, hash e una successiva prova nella chat normale. Se uno fallisce, conservare l'esito e diagnosticare quel caso senza cambiare i criteri o passare ad altri moduli. L'esperimento negativo con la sola policy non viene riclassificato.
