# Misure browser delle risposte sulle note

Primo passo del piano end-to-end: osservare la pagina Note Obsidian senza cambiare il modello, il prompt o il recupero. La chat generale non acquisisce ancora misure di rendering con questa modifica. Voce e prestazioni audio restano da sviluppare.

## Confini osservati

L'avvio della richiesta di risposta, dopo l'eventuale ricerca già completata, usa performance.now nel browser. Il tempo include la preparazione della richiesta nel gestore del pulsante. La ricerca precedente è fuori da questa finestra; il backend recupera nuovamente gli estratti per la risposta.

- headersMs: ricezione delle intestazioni HTTP.
- firstContentMs: primo delta di contenuto non vuoto ricevuto e gestito dal browser. Gli eventi delle fonti non sono testo della risposta.
- firstCommitMs: primo aggiornamento della risposta osservato con useLayoutEffect dopo il commit React nel DOM. Non prova che il browser abbia già dipinto lo schermo e non misura fotoni o attenzione dell'utente. Uno stato React aggiornato non viene contato prima di questo confine.
- totalStreamMs: fine del consumo dello streaming nel client, inclusa la chiusura del reader. Non è un tempo di rendering.
- settledCommitMs: aggiornamento dell'interfaccia dopo lo stato finale della richiesta. Può coincidere con il primo commit per risposte dirette o aggiornamenti raggruppati. Su interruzione esplicita o uscita dalla pagina può restare non disponibile.

I tempi browser e backend hanno inizi diversi e non vengono sommati o sottratti come timestamp dello stesso orologio. L'identificatore x-openjarvis-request-id collega una sola risposta al suo record ASGI. Il recupero delle misure backend è una lettura separata alla fine, senza ritardare testo o generazione. Non ripete l'inferenza né fa polling. Se il record manca, la correlazione rimane esplicitamente non disponibile.

Una misura viene marcata completed solo con contenuto, fine streaming dichiarata da DONE e finish_reason stop. EOF senza DONE o senza stop resta incomplete; length è truncated; errori e cancellazione hanno stati distinti. Il riquadro espandibile Tempi della risposta mostra questi limiti e separa risposta generativa da risposta senza inferenza. Non certifica la qualità dei contenuti.

Una scheda osservata in secondo piano viene marcata ed esclusa dai confronti della latenza dell'interfaccia. L'identificatore di revisione impedisce a chunk e letture delle misure della richiesta precedente di aggiornare una richiesta successiva. La cancellazione conserva il testo parziale e non converte un'interruzione in completamento.

## Privacy e compatibilità

Ultime 50 osservazioni in RAM nel browser, cancellate al ricaricamento; nessuna scrittura in localStorage, database o file. Solo identificatori validati, modalità ammesse, durate finite e stati ammessi. Nessuna query, percorso, nota, risposta, audio o errore testuale nel record. La correlazione copia soltanto sei campi numerici/stato del server, mai il resto dell'oggetto. Il componente offre i dati numerici della singola richiesta per il controllo manuale; non effettua upload o analytics.

Il callback di osservazione SSE è facoltativo. I chiamanti precedenti, inclusa la chat generale, continuano a ricevere gli stessi eventi. Parser, budget, streaming del testo, protezione delle qualifiche datate e modalità breve restano negli stessi percorsi. Nessun cambiamento runtime Python o dipendenze Mac.

## Fonti upstream e validazione di sviluppo

Consultati stato della PR draft e file correnti prima di modificare codice. Consultati [test_stream_bridge.py](https://github.com/open-jarvis/OpenJarvis/blob/1a9c8cf70fbc24872ba2327115040d4c7a99a11a/tests/server/test_stream_bridge.py) per preservazione del risultato senza seconda inferenza e [XRayFooter.tsx](https://github.com/open-jarvis/OpenJarvis/blob/1a9c8cf70fbc24872ba2327115040d4c7a99a11a/frontend/src/components/Chat/XRayFooter.tsx) per visualizzazione separata dei tempi. Non copiati stime di thinking token, metriche cloud o orchestrazione agenti nel profilo locale.

- 26 test frontend mirati passati: 15 nuovi e 11 esistenti. Coperte finestre temporali con orologio controllato, aggiornamento unico finale, assenza di testo, stop/DONE, errori, interruzioni, troncamento, ID errati, whitelist e privacy, limite 50, secondo piano, SSE Unicode spezzato, eventi fonti, payload invariato, ID su errore HTTP, nessuna seconda POST, intestazioni UI e proprietà delle richieste.
- Il test del componente pagina usa un harness dei hook e callback per verificare il collegamento fra ricezione, commit osservato, cancellazione e richiesta successiva. Non è un browser reale o una prova di paint. I due test del riquadro usano rendering React statico.
- 82 test Python/adattatore precedenti passati; parser scalare upstream isolato. Non eseguita l'intera suite upstream o il backend Rust completo.
- Typecheck frontend e build locale Vite/PWA passati nel contenitore con TypeScript JavaScript 5.9.3 e Workbox development, adattamenti di collaudo non distribuiti.

## Collaudo Mac concluso

Installazione del 2026-10-02 riuscita: nove file verificati con backup. Compilazione standard TypeScript, Vite e PWA passata; nuovo bundle della pagina prodotto e avvio sulla porta 8008 raggiunto. La pagina nel browser ha mostrato il riquadro con etichette e dati numerici. Sono stati forniti tre screenshot per i controlli funzionali previsti; nessuno screenshot, testo personale o identificatore di richiesta viene pubblicato.

| Controllo | Primo contenuto browser | Primo commit UI | Fine streaming browser | Stato | Inferenza | Secondo piano |
|---|---:|---:|---:|---|---|---|
| Risposta diretta protetta | 1308,5 ms | 1310,2 ms | 1308,6 ms | completed | false | false |
| Sintesi generativa completa | 27711,2 ms | 27712,7 ms | 60007,3 ms | completed | true | true |
| Sintesi generativa interrotta | 1322,6 ms | 1323,3 ms | 5767,5 ms | cancelled | true | false |

Per la risposta diretta il commit finale è 1310,2 ms. Le misure backend correlate sono recupero 1302,87 ms, primo testo ASGI 1303,4 ms, totale 1303,66 ms, generazione e primo testo della generazione nulli. Stato completed su entrambi i lati.

Per la sintesi generativa completa il commit finale è 60008,2 ms. Backend correlato: recupero 1201,29 ms, primo testo ASGI 27705,8 ms, primo testo dall'avvio del percorso generativo 26504,38 ms, generazione 58802,92 ms, totale 60004,34 ms. Stato completed su entrambi i lati. La scheda è stata osservata in secondo piano: il risultato funzionale viene conservato, ma la prova è esclusa dai confronti di latenza dell'interfaccia. Il backend registra anch'esso un primo testo tardivo: non attribuire l'intera attesa al rendering del browser.

La richiesta successiva è stata realmente interrotta mentre c'era testo parziale. UI Interrotta e stato cancelled coerenti, contenuto parziale ancora presente, nessun completed. Commit finale e server risultano nulli/non disponibili come previsto per l'interruzione esplicita con invalidazione della revisione e annullamento della lettura delle misure. Questo verifica l'interruzione nel client e la sua rappresentazione, **non certifica quanto rapidamente il calcolo Ollama si arresti**.

**Collaudo funzionale circoscritto delle misure sulla pagina Note Obsidian concluso e superato:** percorso diretto, percorso generativo e interruzione distinguibili; correlazione backend presente sulle risposte completate; scheda in secondo piano dichiarata; dati mancanti non trasformati in zeri. Nessun ulteriore ciclo di richieste identiche per ottenere un risultato favorevole.

Non è una baseline comparativa e non certifica la qualità semantica della sintesi libera. La differenza fra il primo testo tardivo della richiesta completa e quello rapido della successiva interrotta è osservata; causa e stato caldo/freddo del modello non sono determinati. Non dichiarato alcun guadagno di velocità per questa strumentazione.

La fase successiva resta l'estensione delle misure alla chat generale, poi la baseline finita del piano end-to-end. Voce non attivata, Jarvis originale intatto, note in sola lettura, PR sempre draft senza merge a main.
