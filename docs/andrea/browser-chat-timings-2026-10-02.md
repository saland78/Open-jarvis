# Misure browser della chat locale

## Comportamento e ambito

La chat locale espone sotto ogni nuova risposta il riquadro espandibile **Tempi della risposta** già usato sulle note. Distingue primo contenuto ricevuto, primo commit DOM del testo, fine streaming e commit finale. Sono confini osservati nel browser, non il paint effettivo dello schermo. I tempi ASGI sono correlati soltanto attraverso l'ID della richiesta: nessuna somma fra orologi e nessuna ulteriore generazione per ottenere le misure.

Il registro di chat associa la richiesta al messaggio assistente e alla conversazione originaria, separatamente da ChatMessage, MessageTelemetry e dal salvataggio delle conversazioni esistente. Mantiene al massimo 50 associazioni e snapshot numerici in RAM; il registro comune delle osservazioni resta limitato a 50. Non aggiunge persistenza, query, testo delle risposte, note o percorsi. Gli identificativi di proprietà restano nel registro RAM e non entrano nei dati numerici del pannello. Una ricarica cancella le osservazioni; le risposte storiche ricaricate non ricevono tempi inventati.

Il percorso locale consuma anche il marcatore SSE `[DONE]` dopo `finish_reason`: il solo `stop` non certifica che il trasporto sia concluso. EOF senza DONE è incompleto, `length` è troncato, cancellazione ed errore sono distinti. Il percorso non locale mantiene il precedente comportamento. La modalità research non riceve queste nuove misure.

Se viene aperta un'altra conversazione, il registro conserva la proprietà originale e segnala che i commit successivi non sono misurati. Riaprire una risposta storica non diventa una misura del suo primo rendering. La scheda in secondo piano è marcata separatamente. Entrambi i casi vanno esclusi dai confronti dell'interfaccia. In caso di interruzione il commit finale resta non disponibile: la conferma della cancellazione del client non prova l'arresto istantaneo del calcolo Ollama.

Una richiesta fermata che termina dopo l'avvio della successiva non può sovrascrivere il nuovo placeholder o azzerare lo stato del suo stream. La lettura delle misure backend è singola, separata e non blocca la risposta. Dati mancanti restano dichiarati non disponibili, senza polling o tentativi di abbinamento ad altre richieste.

Modello, prompt, runtime Python, budget, note, guardia sulle qualifiche e dipendenze non vengono modificati. Questa fase aggiunge osservazioni, non dimostra un miglioramento prestazionale o la correttezza universale delle risposte.

## Consultazione e verifiche di sviluppo

Prima della modifica verificati branch e PR draft del fork su GitHub. Consultati nuovamente `frontend/src/lib/store.stream-ownership.test.ts` e `frontend/src/lib/chat-telemetry.test.ts` upstream al commit `1a9c8cf70fbc24872ba2327115040d4c7a99a11a`. Il primo verifica proprietà dello stream in conversazione non attiva e protezione della sua cancellazione; il secondo conserva la risoluzione dell'engine. Riutilizzati osservatore SSE e misure numeriche già collaudati nella pagina Note Obsidian, senza importare indiscriminatamente funzionalità upstream.

38 test frontend mirati passati: nuova integrazione del submit reale tramite harness di hook/callback, proprietà del registro e limiti RAM, disclosure statico del pannello chat, regressioni delle note/SSE, profilo locale e test upstream di proprietà/telemetria. Verificati DONE, EOF, troncamento, annullamento con frammenti tardivi e nuova risposta, cambio conversazione, percorso non locale e mancata aggiunta di tempi ai messaggi salvati. L'harness non è un browser reale e non verifica il paint. Suite upstream completa non eseguita; backend invariato.

Typecheck e build Vite/PWA nel contenitore passati con TypeScript JavaScript 5.9.3 e Workbox development per i limiti dell'ambiente. Questi adattamenti non vengono distribuiti: il Mac mantiene la compilazione standard. L'installer usa la transazione verificata con hash, baseline, backup e rollback, porta 8008 libera; nessuna dipendenza o dato personale incluso.

## Collaudo Mac ancora da eseguire

Installazione, build standard e tre controlli funzionali finiti: risposta completa con pannello e correlazione backend; cambio conversazione durante la risposta con proprietà conservata; interruzione dopo il primo testo. Nessuno di questi è già dichiarato superato. Successivamente la baseline end-to-end prevista dal piano usa casi sintetici e distingue primo testo e durata totale, senza riclassificare misure in secondo piano o cancellate come confronti prestazionali validi.
