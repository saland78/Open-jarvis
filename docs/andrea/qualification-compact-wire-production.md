# Trasporto compatto della sintesi delle qualifiche

Stato al 2026-10-04: integrato e verificato in sviluppo dopo il confronto Mac superato. **Non ancora installato né misurato nel browser sul Mac.** La preservazione della frase corrente è già collaudata nel caso reale precedente; il presente intervento riduce il trasporto generato mantenendola.

## Comportamento finale

Il ponte `note_facts.run` usa la candidata riesaminata soltanto per una nota scelta con qualifiche riconosciute e attive. L'estrattore continua a produrre quattro fatti comprovati. Prima dell'inferenza il programma lega l'intera frase corrente e le due date ai passaggi originali. Il modello restituisce esclusivamente F1, F2 e F4 come stringhe; il programma compone quattro punti con F3 dalla fonte e rende visibili le origini.

La frase corrente rimane contrassegnata «Frase riportata dalla fonte», con indicazioni complete su periodo, titolo e marketplace. Date e citazioni provengono dai passaggi originali. Le altre tre stringhe sono sintesi del modello: entrano identiche nel validatore esistente, senza riscrittura o completamento dei campi mancanti. Le qualifiche corrente/storica restano distinte; assenza non equivale a zero o a indisponibilità nella dashboard.

Il profilo del libro conserva messaggi, schema e percorso precedenti. Chat, ricerca, passaggi brevi, frontend, modello, contesto, budget, impostazioni Ollama, dati e dipendenze sono invariati. Nessun motore, agente, strumento o servizio esterno aggiuntivo abilitato.

## Confini conservati

La risposta rimane trattenuta finché lo stream non termina e il validatore non accetta il contratto. Dopo la generazione il ponte rilegge l'intera nota e controlla identità del vault, testo, stato, inizio del corpo e data del file. Una variazione anche fuori dai passaggi selezionati rifiuta la risposta. La candidata viene ricalcolata dalle prove originali, senza fidarsi di date, schema o metadati modificati.

Chiavi mancanti, duplicate o extra, vecchio envelope, valori errati, stream troncati/incompleti, tool call e superamento dei limiti producono rifiuto; nessuna seconda generazione. Cancellazione, timeout e vincolo di singola richiesta conservano il percorso protetto. I controlli tecnici non certificano il significato di ogni futura frase: `pending_review` resta distinto dalla revisione delle risposte osservate.

## Evidenza e verifiche

Il [confronto Mac](qualification-compact-wire-experiment.md#confronto-reale-concluso-e-superato--2026-10-04) usa due note sintetiche pubbliche, quattro richieste, nessun retry. Entrambe le coppie superano token e durata nativa di produzione, con revisione favorevole di tutte le risposte sui quattro fatti richiesti. I [numeri e testi sintetici filtrati](qualification-compact-wire-mac-2026-10-04.json) mantengono separati esito automatico e manuale; nessuna cronologia personale pubblicata.

**168 test Python passati** per trasporto compatto, ponte ASGI/vault reale con modello simulato, guard della frase completa, prove precedenti e aggiornamenti storici, adattatori, raccolta e runtime strutturato. Sono inclusi il replay senza inferenza delle due risposte compatte osservate sul Mac attraverso il vero percorso ASGI, quattro fatti e origini, fonte cambiata dopo lo stream, schema nativo, chiavi incomplete/duplicate e rifiuto senza retry. Gli archivi test-only ricostruiscono gli hash originali dei vecchi probe e installer; non indeboliscono i loro controlli e non vengono distribuiti al Mac.

Il helper adottato conserva byte per byte tutte le istruzioni, costanti e funzioni della candidata; cambia soltanto il docstring che ne descrive l'uso. Nessuna build frontend necessaria per i due sorgenti Python. Non sono eseguiti Ollama reale, browser Mac o intera suite upstream in questo ambiente.

Consultati nuovamente upstream al commit `a0df94cd93756047c724d803662bc671618b10d4`: [test_structured_output.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_structured_output.py) e [test_stream_bridge.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/server/test_stream_bridge.py). Si mantiene schema nativo nel motore e il risultato della singola inferenza, con validazione indipendente; nessuna installazione indiscriminata dell'upstream.

## Collaudo Mac finito ancora da eseguire

Preparare un aggiornamento di soli `qualification_compact_wire.py` e `note_facts.py`, da un commit immutabile con hash, backup e rollback. OpenJarvis deve essere fermo durante la sostituzione. Dopo l'avvio usare la stessa nota KPI e il pulsante di sintesi della nota scelta, una volta: verificare quattro punti, frase corrente, date e passaggi; annotare tempi browser/backend e leggere le fasi native della medesima inferenza con il lettore esistente. Quella lettura non genera un'altra risposta.

Qualità, accettazione tecnica e latenza reale sono criteri distinti. Non dichiarare già misurato un guadagno nel browser; evitare confronto causale con un solo campione che ha cache/caricamento diversi. Se fallisce, conservare risposta/rifiuto e diagnosticare prima di continuare altri task. PR #1 rimane draft e non unita; Jarvis originale resta indipendente.
