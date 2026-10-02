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

## Collaudo Mac ancora da eseguire

Installazione e build standard prima della verifica reale. Aprire Note Obsidian, con scheda in primo piano, e controllare il riquadro per una risposta diretta già nota: tempi browser presenti, aggiornamenti UI presenti, stato completed, inferenceUsed false e correlazione allo stesso ID. Nessuna richiesta di nuova generazione per certificare il funzionamento del riquadro su quel percorso.

Successivamente una risposta che dichiari effettivamente model_synthesis deve distinguere primo contenuto dal totale, mantenendo lo stesso modello e i criteri di qualità. Un'interruzione deve avere cancelled e conservare la risposta parziale senza mostrare completed. Se la risposta termina prima del clic di interruzione, non è una prova di cancellazione: usare una richiesta generativa senza ripetere fino a ottenere tempi favorevoli. Questa verifica funzionale non è una serie di benchmark o una certificazione semantica universale.

La baseline comparativa del piano end-to-end viene dopo l'estensione alla chat e la chiusura di questi confini. Nessun guadagno di latenza dichiarato per questa sola strumentazione. I risultati Mac devono essere registrati prima di considerare concluso il passo. Jarvis originale intatto, note in sola lettura, PR sempre draft senza merge a main.
