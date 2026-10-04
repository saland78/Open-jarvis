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

**Collaudo del candidato sul Mac ancora da eseguire.** Nessuna correzione installata o qualità già dichiarata superata. Se i tre criteri passano, preparare l'aggiornamento della sola policy con backup, hash e successiva prova nella chat normale. Se uno fallisce, conservare l'esito e diagnosticare quel caso senza cambiare i criteri o passare ad altri moduli.
