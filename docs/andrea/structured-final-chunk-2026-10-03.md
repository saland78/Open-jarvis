# Correzione del messaggio finale della sintesi strutturata

## Esito Mac del 2026-10-02: collaudo funzionale fallito

Aggiornamento di 10 file completato con backup e build standard Mac riuscita. Sei richieste attraverso il backend reale completate nel trasporto; i due casi diretti (vendite documentate e conteggi discordanti) superano i criteri. Tutte e quattro le richieste generative producono `structured_refused`, con `structuredAcceptedTextMs=null`: non rispondono ai criteri del test. Nessuna risposta rifiutata va riclassificata come successo della sintesi. Le affermazioni del modello non sono state esposte; il loro contenuto non è nel rapporto e non è valutabile da questo output.

Il rapporto numerico filtrato conserva categorie e tempi, senza storico Terminale, risposte o request ID. La prima richiesta termina in circa 39 s, le altre generative in circa 14,4 / 6,9 / 6,7 s. Questi tempi sono tempi di rifiuto, non risposte accettate. Nessun miglioramento di latenza dichiarato.

## Causa e modifica circoscritta

Consultati nuovamente su GitHub il tipo `StreamChunk`, l'engine Ollama e `tests/engine/test_ollama.py` upstream. `StreamChunk.content` è opzionale e vale `None` per il frame terminale con finish_reason/usage. L'engine `_run_stream` emette proprio `StreamChunk(finish_reason=..., usage=...)`. Il raccoglitore introdotto nel fork rifiutava `None` prima di leggere finish_reason, quindi validava con `completed=false` anche un JSON completo.

La modifica riguarda soltanto `scripts/andrea/structured_stream.py`: converte `content is None` in assenza di testo e continua a controllare il completamento. Non converte tipi diversi o JSON incompleti in successo e non allenta il validatore di fonti/date. Prompt, modello, budget, ricerca, guardie deterministiche e frontend invariati. Non basta questo per dichiarare le risposte del modello semanticamente corrette.

## Riproduzione e verifica

Nuovi test isolano dagli import nativi il tipo StreamChunk reale e i metodi effettivi `stream_full`/`_run_stream`; sostituiscono solo il trasporto HTTP. Prima della modifica due casi falliscono: JSON completo con frame terminale None e scansione post-hoc dopo tale frame. Dopo la modifica tutti e cinque passano: terminale valido, EOF/troncamento, strumenti vietati, chunk vuoto senza completamento e contenuti non stringa, scansione dopo il terminale.

I test ASGI precedenti sono corretti per usare `None` nei frame terminali. Regressione completa del profilo: **107 test passati**, con nessuna lettura di note personali o inferenza reale nel contenitore. La correzione non modifica l'interfaccia, perciò non richiede una nuova build frontend. Nessun adattamento dev del contenitore distribuito.

Lo script di aggiornamento installerà **un solo file** da un commit preciso, verificando hash e baseline, porta 8008 libera e backup. I test del manifest reale devono comprendere applicazione, backup, sentinelle, ripetizione, errore di sostituzione, hash errato, baseline incompatibile e porta occupata.

## Chiusura ancora necessaria

Installare sul Mac, riavviare e ripetere una volta la raccolta finita di sei casi con `check_structured.py`. Rivedere le affermazioni rispetto agli estratti originali: completamento, validità strutturale e qualità restano esiti distinti. Poi un controllo della pagina Note Obsidian e dei tempi. Nessun retry automatico, no note/db/profili modificati, niente merge della PR draft. Il precedente esito negativo resta registrato.
