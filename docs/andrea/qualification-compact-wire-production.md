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


## Aggiornamento verificato pronto

Payload immutabile: `90dc3f0bb4a1727ba4cb01ed9ed72916e5904d28`. Installer `scripts/andrea/update_compact_qualifications.py`, SHA-256 `0deec43be0302b78b2a2d5d4ed4ed6cc98bdc4d7f974239db305243c1bbf2cc9` (8875 byte). Scarica e verifica prima di sostituire questi due file:

| Sorgente | SHA-256 nuovo | Baseline richiesta |
|---|---|---|
| `qualification_compact_wire.py` | `8ace1bc1a79345ee1efc4fb34f642808c5e610fd5b073c6ca960b15716abca98` | Assente o già identico |
| `note_facts.py` | `e259adc3b46112a9516b3f41bd8dc1628a5676fcfff051cb1ba0ae343d6bdbe8` | `b2524d94ccbc7ab15e9d21e67ed91433cf6a37bedfe395aa6e27cbd46ea52ee7` oppure nuovo identico |

Undici componenti immutabili, compresi i due guard e il frontend già compilato, sono verificati prima e dopo il download. Sintassi di ogni payload Python verificata prima dell'applicazione. Porta 8008 libera richiesta; nessun processo terminato automaticamente. Backup di ogni file precedente, sostituzione atomica di ciascun file e rollback della transazione se fallisce. Un helper nuovo viene rimosso dal rollback; il vecchio ponte viene preservato. Modifiche locali incompatibili, file mancanti, hash errati, symlink o modifiche concorrenti rilevate interrompono l'aggiornamento senza sovrascriverle.

**Dieci test del manifest reale passati**, aggiunti alle 168 regressioni: applicazione/ripetizione, backup e permessi, dati/configurazioni sentinella invariati, hash errato del secondo download, collisione/mancanza, porta occupata e symlink, errore al secondo rimpiazzo e rimozione del helper, modifica dei guard o del ponte durante download, sintassi non valida con hash coerente e ciascuna dipendenza incompatibile. Totale dei controlli pertinenti passati: **178**. Gli artefatti di sorgente sono riletti integralmente dal commit pubblicato; nessun payload personale incluso.

Il primo passo Mac successivo è fermare solo il Terminale OpenJarvis e lasciare Controlli aperto. Fornire poi separatamente download con URL semplice e checksum, esecuzione, avvio e una sintesi reale. Non presumere lo script già scaricato o il Mac aggiornato. Non richiedere una nuova build frontend per questo aggiornamento Python.
