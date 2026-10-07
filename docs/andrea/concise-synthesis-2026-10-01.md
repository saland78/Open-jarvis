# Sintesi più concise: preparazione e criteri — 2026-10-01

## Problema e cambiamento

La baseline successiva all'ottimizzazione del recupero mostra circa 0,81 secondi di ricerca e 24,35 secondi totali per la sintesi sulle note. La generazione rimane la parte più lunga. Il prompt precedente consentiva fino a sei frasi, anche quando una domanda semplice richiedeva una risposta molto breve.

NOTES_RESPONSE_STYLE separa lo stile dalle regole sulle evidenze: risposta immediata, normalmente 2–3 frasi e circa 60 parole, senza introduzioni, ripetizioni o conclusioni generiche. Se servono più parole per coprire i punti richiesti, date, conflitti o limiti, completezza e citazioni hanno priorità. Un dato mancante richiede una dichiarazione con fonte e limite pertinente, non una panoramica estranea.

È una guida al modello, non un limite automatico alle parole. Il testo dello stream non viene tagliato dopo la generazione; una citazione o una precisazione finale deve sopravvivere anche in una risposta più lunga. Non è garantito che il modello rispetti sempre lo stile o che risponda più velocemente.

Le regole sulle fonti restano identiche, salvo la rimozione del precedente limite di sei frasi: conflitti espliciti, modifiedAt non come prova, date dichiarate, dato assente diverso da zero, attribuzione delle opinioni, recensioni non come vendite, presupposti falsi della domanda, limiti degli estratti e nessuna esecuzione di istruzioni nelle note. Gli estratti e i metadati forniti al modello sono invariati. Il percorso dei conteggi espliciti, la ricerca appena ottimizzata e la chat ordinaria non sono modificati.

Restano qwen3:4b-instruct-2507-q4_K_M, contesto 4096, massimo 512 token, temperatura 0,4, thinking disattivato e timeout 90 secondi. Non si abbassa il budget per ottenere una risposta troncata. Nessuna nuova cache, dipendenza o chiamata esterna.

## Verifiche tecniche

Prima della modifica sono consultati tests/evals/scorers/test_doc_qa.py e tests/engine/test_ollama.py dell'upstream, commit c4da16e1ca3d21f4cc1905d4200063e564104f0f. I controlli su fatti, citazioni e streaming restano separati. I test upstream non certificano il significato di una nuova risposta del modello.

Passano 55 verifiche mirate, incluse due nuove prove ASGI: chat con messaggi originali e budget conservati, note con estratti completi e stile applicato; stream simulato lungo con citazione finale conservata integralmente e stato completed. Le altre prove mantengono conflitti, conteggi diretti, esclusioni, righe, ricerca incompleta, timeout, annullamento e troncamento. Il parser upstream è eseguito in isolamento nella checkout parziale; non si dichiara eseguita l'intera suite upstream o il backend Rust completo.

La verifica tecnica non simula l'obbedienza del modello né misura un'accelerazione reale. I sei casi e criteri in quality_cases.json restano identici. La modifica non è ancora installata e la nuova qualità con Ollama sul Mac è da verificare.

## Aggiornamento e collaudo finito

update_concise.py installa runtime.py, test_andrea_concise.py e questo documento da un commit fissato, con hash, baseline, backup e rollback. Richiede porta 8008 libera. Nessun cambiamento a note, configurazioni, database, dipendenze o frontend. La PR resta draft e Jarvis originale resta separato.

Ordine del controllo sul Mac:

1. Installazione verificata e riavvio.
2. Sei casi di qualità immutati, con revisione del significato oltre ai controlli formali. I tre casi senza inferenza devono conservare l'esito; i tre con modello verificano dato non verificato, problema passato risolto e royalty non documentate. Un criterio fallito blocca l'approvazione della modifica.
3. Solo dopo l'esito di qualità, la stessa raccolta di tre chat brevi e tre sintesi con notes-query "kpi self publishing", confrontata con search-work-mac-review-2026-10-01.md. Anche le risposte non troncate devono avere citazioni e informazioni necessarie nella verifica separata; un minor tempo da solo non basta.
4. Un riassunto della medesima nota nell'interfaccia confrontato con gli estratti per controllare concisione e completezza su fonti reali.

Successo: criteri invariati rispettati, nessun nuovo troncamento, contenuti necessari e fonti conservati, riduzione osservata del tempo totale delle sintesi. Circa 60 parole è un obiettivo, non un criterio che autorizza omissioni. Tre misure non garantiscono prestazioni universali. Se non migliora il tempo o peggiora la qualità, il backup permette il ritorno al runtime precedente; non si ripete la suite invariata fino a ottenere un esito favorevole.

Non è stato verificato un nuovo miglioramento della latenza, alcun dato KDP esterno o apprendimento del modello. Acquisizione audio, STT e TTS restano funzioni future.
