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

## Collaudo Mac concluso

Installazione del 2026-10-02 completata: dieci file verificati e backup creato. Compilazione standard `tsc -b && vite build` riuscita, 3486 moduli trasformati, build Vite in 1,40 secondi e PWA generata. Il launcher è arrivato all'avvio sulla porta 8008; le successive schermate confermano che l'interfaccia aggiornata è raggiungibile.

I tre controlli funzionali previsti sono stati eseguiti sul Mac. Sono registrate soltanto misure e categorie: screenshot, prompt, risposte e identificativi non vengono pubblicati. Nella tabella i valori sono arrotondati ai millisecondi, come mostrati nel pannello; per la prima prova è disponibile anche il dettaglio numerico.

| Controllo | Primo contenuto browser | Primo commit UI | Fine streaming browser | Stato mostrato | Commit finale |
|---|---:|---:|---:|---|---:|
| Risposta completa | 15365 ms | 15382 ms | 15725 ms | Completata | 15744 ms |
| Cambio conversazione | 944 ms | 952 ms | 55886 ms | Completata | Non disponibile |
| Interruzione | 743 ms | 754 ms | 4506 ms | Interrotta | Non disponibile |

**Risposta completa:** browser e backend hanno stato `completed`, con correlazione delle misure disponibile. Scheda non osservata in secondo piano. Dettaglio browser: headers 95,5 ms, primo contenuto 15365 ms, primo commit 15381,9 ms, streaming 15724,8 ms, commit finale 15743,7 ms. Backend: primo testo 15361,9 ms, primo testo del percorso generativo 15361,73 ms, generazione 15724,68 ms, totale 15724,84 ms. Recupero note nullo, coerentemente con il percorso di chat.

**Cambio conversazione:** la risposta e il riquadro restano sulla conversazione originaria. Il pannello segnala esplicitamente che è stata aperta un'altra conversazione e che i commit successivi non vengono misurati. Il commit finale non disponibile non viene inventato al ritorno. È mostrato anche l'avviso di scheda in secondo piano: questa prova è esclusa dai confronti di latenza dell'interfaccia. Backend visibile nel pannello: primo testo 938 ms e totale 55882 ms, valori arrotondati.

**Interruzione:** stato UI Interrotta, testo parziale conservato e casella del messaggio nuovamente disponibile. Commit finale e misure backend non disponibili, con relativa spiegazione, senza dichiarare la risposta completa o trasformare i dati mancanti in zeri. Non è mostrato l'avviso di scheda in secondo piano. Questo verifica la cancellazione del client, non la rapidità di arresto del calcolo Ollama.

**Collaudo funzionale circoscritto delle misure della chat generale concluso e superato.** Nessun ulteriore ciclo delle stesse prove per ottenere tempi favorevoli. La variabilità del primo testo è osservata; causa e stato caldo/freddo del modello non sono determinati. Non è una baseline comparativa né una certificazione semantica universale delle risposte. Le precedenti limitazioni e gli esiti negativi della sintesi libera restano documentati.

Il passo successivo è la baseline finita del piano end-to-end: distinguere primo contenuto e tempo totale su casi sintetici comparabili. Nessuna ottimizzazione del modello o funzione vocale viene dichiarata completata da questo collaudo. Consultati nuovamente stato GitHub e test upstream di proprietà dello stream prima di registrare l'esito. Nessun codice ulteriore modificato, PR sempre draft senza merge a main; Jarvis originale intatto.
