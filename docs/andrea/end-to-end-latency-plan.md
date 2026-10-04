# Piano modulare della latenza end-to-end

Direzione confermata da Andrea il 2026-10-02: ottimizzare il percorso completo della richiesta, privilegiando elaborazione locale, operazioni asincrone utili e trasferimenti minimi. Ridurre l'attesa senza perdere qualifiche, citazioni o gestione degli errori. Questo documento è un piano: la voce non è ancora attiva nel profilo Andrea.

## Stato e misure

Il percorso oggi operativo è browser → backend locale → recupero eventuale delle note → preparazione del contesto → Ollama eventuale → eventi SSE → browser. Le risposte estrattive e i conteggi diretti non avviano inferenza e devono essere misurati separatamente dalle sintesi del modello.

Sono già disponibili misure ASGI di recupero, primo testo, generazione e completamento. Non equivalgono al primo testo visibile nel browser. Il tempo di generazione osservato comprende il percorso della richiesta al motore; non rappresenta necessariamente il solo calcolo del modello. I chunk SSE non sono token.

Il percorso vocale futuro aggiunge attivazione, acquisizione, riconoscimento della fine della frase, preprocessing, trascrizione, sintesi vocale e riproduzione. Distinguere tempo dall'attivazione al primo audio e tempo dalla fine del parlato al primo audio: il primo include anche la durata della frase pronunciata dall'utente.

Le fasi possono sovrapporsi: il totale va misurato ai suoi estremi, non ottenuto sommando durate sovrapposte. Browser, server e dispositivo hanno orologi diversi: usare durate locali monotone e un ID correlato, senza sottrarre timestamp di macchine diverse.

## Moduli e responsabilità

| Modulo | Responsabilità | Misura o criterio |
|---|---|---|
| Interfaccia | Invio, primo testo reso visibile, cancellazione | Invio → primo rendering; invio → completamento |
| Coordinamento locale | Routing, code, contesto, limiti e stati | Attesa in coda distinta dal lavoro; una generazione per volta |
| Conoscenze | Ricerca, lettura, selezione degli estratti | Recupero separato; freschezza del file distinta dai fatti |
| Motore | Richiesta Ollama, primo contenuto, fine | Primo contenuto e totale distinti; token solo se realmente disponibili |
| Audio in ingresso, futuro | Microfono, buffer, fine frase, preprocessing | Nessun parlato perso; ritardo dopo la fine della frase |
| STT, futuro | Trascrizione e stato finale | Primo parziale e testo finale; errori di trascrizione |
| TTS e uscita, futuri | Frasi pronunciabili, buffer, ordine, stop | Primo campione riprodotto; pause e cancellazione effettiva |

Un ID di richiesta accompagna i moduli. La cancellazione deve invalidare anche audio accodato appartenente alla richiesta precedente. Code limitate e gestione della pressione evitano accumulo senza controllo. Errori e timeout rimangono distinguibili dal completamento.

Le misure restano numeriche e locali, senza salvare audio, testi personali o contenuti delle note. Nessun upload o fallback cloud implicito.

## Ordine di lavoro e criteri di chiusura

1. **Completare l'osservazione del percorso testuale.** Aggiungere misure nel browser per primo testo visualizzato e completamento, correlate con i tempi già presenti nel backend. Coprire risposta generata, risposta diretta e cancellazione/errore. Non cambiare contemporaneamente modello o prompt. Criterio: misure distinguibili e coerenti, nessun testo privato nelle registrazioni.
2. **Baseline finita.** Tre richieste per ciascuno di tre percorsi: chat generata, note sintetiche con generazione e note sintetiche dirette. Totale nove richieste, senza ripetere fino a ottenere un risultato favorevole. Marcare primo utilizzo e richieste successive senza dichiarare caldo/freddo se non osservabile. Riportare singole misure e mediana, non percentili affidabili da tre campioni. Errori e risposte troncate restano nel rapporto.
3. **Una modifica per volta dove le misure mostrano il costo.** Valutare prima code, recupero, contesto e lavoro ridondante. Riutilizzo del modello e componenti va verificato; non scaricare o riconfigurare globalmente Ollama condiviso. Ripetere solo i percorsi interessati, con gli stessi criteri di qualità e un ripristino pronto. Più veloce ma semanticamente peggiore è un test fallito.
4. **Prima voce locale con attivazione manuale.** Valutare componenti upstream e compatibilità con Mac Intel prima di scegliere STT/TTS o installare dipendenze. Collaudo breve con registrazioni sintetiche e permesso microfono esplicito. La parola di attivazione continua viene dopo, quando errori e risorse sono misurabili.
5. **Sovrapposizione controllata.** Solo dopo una baseline audio corretta: confrontare chunk e attesa di fine frase, esecuzione non bloccante, trascrizioni parziali ed emissione TTS per frasi complete. I parziali STT non autorizzano azioni irreversibili. Non leggere ad alta voce una qualifica incompleta o un risultato che il percorso protetto deve trattenere. La sola punteggiatura non verifica la verità di una frase.
6. **Collaudo dell'interazione completa.** Misurare attivazione → primo audio, fine parlato → primo audio, totale, interruzione e presenza di pause. Cambiare i buffer solo sulla base del compromesso osservato fra rapidità, qualità e stabilità; nessuna dimensione universale viene promessa.

La voce non deve compromettere l'uso testuale. Ogni nuovo modulo resta disattivabile senza reinstallare il progetto. Memoria, automazioni e proattività seguono i loro collaudi separati: non fanno parte di un aggiornamento indiscriminato per la latenza.

## Consultazione upstream per questo task

Sorgenti consultati al commit upstream 1a9c8cf70fbc24872ba2327115040d4c7a99a11a:

- [voice_io.py](https://github.com/open-jarvis/OpenJarvis/blob/1a9c8cf70fbc24872ba2327115040d4c7a99a11a/src/openjarvis/speech/voice_io.py): acquisizione a chunk, rilevamento silenzio e riproduzione. Il codice letto accumula registrazione WAV prima di restituirla e aspetta la fine della riproduzione; non dimostra una pipeline end-to-end già ottimizzata sul Mac Andrea. I valori predefiniti non vengono copiati come obiettivi prestazionali.
- [phase_metrics.py](https://github.com/open-jarvis/OpenJarvis/blob/1a9c8cf70fbc24872ba2327115040d4c7a99a11a/src/openjarvis/telemetry/phase_metrics.py): separazione delle finestre prima e dopo il primo token. Valutare il riuso delle idee, senza attivare raccolta energetica o persistenza non necessaria.
- [test_stream_bridge.py](https://github.com/open-jarvis/OpenJarvis/blob/1a9c8cf70fbc24872ba2327115040d4c7a99a11a/tests/server/test_stream_bridge.py): regressione che conserva il risultato già prodotto senza una seconda inferenza. La stessa regola guida l'eliminazione del lavoro ridondante; non abilita agenti o strumenti nel profilo locale.

Questa consultazione non equivale a esecuzione dei test upstream o collaudo vocale. Nessun codice runtime, dipendenza, profilo o nota modificato per approvare il piano. Jarvis originale resta indipendente; PR draft da non unire.

## Task futuri collegati

La [roadmap dei moduli web, Amazon, controllo Mac e vocali WhatsApp](future-capabilities-roadmap.md) raccoglie i requisiti successivi. Sono task da progettare e collaudare, non funzioni attivate. La priorità immediata resta distinguere caricamento, preparazione del contesto e generazione nella richiesta di sintesi reale, quindi adottare una sola ottimizzazione che mantenga i criteri di qualità.

## Aggiornamento operativo del 2026-10-04

La [raccolta delle fasi native in produzione](production-native-phases.md) è conclusa: un caso reale della nota scelta, confronto semantico favorevole, contratto accettato e misure dalla stessa inferenza disponibili. Nessuna inferenza aggiuntiva effettuata dal lettore. Caricamento circa 5,84 s, contesto 14,99 s, produzione 20,36 s; contatore cache dichiarato zero. Queste misure non dimostrano un miglioramento o la causa della variabilità precedente.

Prima di un'ulteriore modifica al prompt, il prossimo task è verificare con un confronto finito il riuso del modello e del contesto sul medesimo percorso di produzione. Conservare gli stessi fatti, schema, modello e criteri semantici; niente unload, retry o ripetizioni fino a ottenere un esito favorevole. La raccolta appena conclusa non richiede ulteriori prove per la sua chiusura. Voce, strumenti e moduli futuri seguono il loro ordine separato.

## Chiusura del confronto del riuso — 2026-10-04

Una sola nuova sintesi sul percorso della nota scelta conferma il riuso nel caso esaminato: Ollama dichiara 795 token in cache su 796, caricamento 1,734 ms, valutazione 152,761 ms, produzione 19237,198 ms; totale backend 19433,17 ms. Revisione semantica favorevole dei quattro fatti selezionati. Nessun cambiamento runtime, unload, warm-up forzato o retry. Tempi UI esclusi per scheda osservata in secondo piano, senza nuova prova. [Rapporto completo e numeri](production-native-phases.md#confronto-del-riuso-in-produzione-concluso-e-superato).

Il costo residuo dominante è la produzione dei token. Prossimo candidato, ancora da progettare e collaudare: testi generati più concisi sul solo percorso riconosciuto delle qualifiche datate, preservando i medesimi fatti obbligatori, ambito, qualifiche, date, fonti e validatore. Non sostituire il controllo con troncamento o visualizzazione di JSON non validato. Il precedente esperimento CPU sui thread è concluso senza guadagni utili: automatismo mantenuto e nessuna nuova ripetizione necessaria. Non sono state eseguite prove della candidata per questa chiusura.


## Chiusura della candidata di stile e diagnosi del riferimento — 2026-10-04

Il [confronto finito](concise-qualification-text-experiment-2026-10-04.md) non supera le soglie: 136 token contro 136 nell'ordinario, 134 contro 131 nell'avversariale, e durata nativa di produzione leggermente peggiore per entrambe le candidate. Il riferimento avversariale ha un contratto rifiutato per unsupported_value_update. Nessuna modifica della produzione, nessuna nuova prova CPU o ripetizione di questa candidata. I totali influenzati da cache/caricamento non cambiano l'esito.

Prima di progettare un'altra modifica di latenza, ottenere evidenza del rifiuto con [una singola diagnosi sintetica distinta](qualification-rejection-diagnostic.md): il rapporto precedente non conserva il JSON rifiutato e non consente di attribuire la causa a una frase concreta. Un nuovo campione accettato non supera retroattivamente la prova precedente. Test di trasporto e formato restano distinti dall'equivalenza del significato. Non rendere il validatore meno rigoroso per far passare una risposta sconosciuta.



## Diagnosi conclusa, priorità alla preservazione dell'informazione — 2026-10-04

La [singola richiesta diagnostica](qualification-rejection-diagnostic.md#esito-reale-della-singola-richiesta) termina senza riprodurre il rifiuto, ma non risolve la causa precedente. La frase generata omette il predicato di persistenza presente nella fonte: il passaggio dai controlli tecnici non certifica equivalenza completa. Nessuna altra ripetizione della candidata di stile, né richiesta supplementare sul caso diagnostico.

Il prossimo intervento è definire un contratto circoscritto che preservi predicato e ambito della qualifica, separando chiaramente gli elementi sostenuti dalla fonte dalla prosa generata. Non è ancora implementato o adottato. Dopo i controlli di preservazione, valutare la rimozione di metadati ridondanti dal JSON generato per ridurre il lavoro del modello; conservare le associazioni alla fonte e non chiamare quei metadati apprendimento autonomo. Prestazioni e qualità richiedono esiti distinti, con criteri fissati prima della raccolta.
