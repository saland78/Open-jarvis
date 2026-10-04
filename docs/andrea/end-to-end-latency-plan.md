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

Il collaudo della [correzione del solo prefisso](qualification-clause-fix.md#esito-reale-del-collaudo-mac) conserva predicato e ambito ma fallisce la qualità completa omettendo la consultazione. Nessuna adozione. Il lavoro attivo è la [protezione della frase completa dalla fonte](qualification-sentence-fix.md), compresi periodo, titolo e marketplace: prova sintetica Mac superata con revisione del significato, 148 controlli Python e 12 dell’interfaccia superati. Integrazione installata, compilazione completa riuscita sul Mac e singola prova reale superata nel confronto con tutti i passaggi selezionati. Vedi il [collaudo di produzione](qualification-sentence-production.md). La correzione è chiusa nel caso osservato: circa 45,29 s fino alla risposta UI. Si può riprendere il task latenza con gli stessi fatti e controlli; nessun nuovo confronto è già stato effettuato. Dopo i controlli di preservazione, valutare la rimozione di metadati ridondanti dal JSON generato per ridurre il lavoro del modello; conservare le associazioni alla fonte e non chiamare quei metadati apprendimento autonomo. Prestazioni e qualità richiedono esiti distinti, con criteri fissati prima della raccolta.

## Preparazione della prova con meno campi generati — 2026-10-04

La [candidata isolata](qualification-compact-wire-experiment.md) richiede soltanto F1/F2/F4 come stringhe. F3 completo e date provengono dai passaggi già comprovati prima dell'inferenza; restano nella risposta e sono dichiarati come contenuti della fonte. Ricomposizione dei quattro record e validatori di produzione invariati, nessuna riparazione del testo del modello. 16 nuovi test e 148 regressioni passati, compreso trasporto HTTP simulato. Nessuna modifica alla produzione o misura reale già eseguita.

Prima leggere le fasi native della richiesta da 45,29 s già presente in RAM: il lettore non genera risposte. Il confronto successivo prevede quattro richieste sintetiche al massimo in ordine A/B e B/A, nessun retry, soglie del 20% su token e decoding in entrambe le coppie e revisione separata dei quattro fatti. Prestazioni native favorevoli non bastano a certificare latenza UI o qualità: l'eventuale adozione richiede il mantenimento della rilettura della fonte e dei confini ASGI e una verifica sul percorso reale. Nessun nuovo task funzionale viene attivato da questa prova.


## Adozione del trasporto compatto — 2026-10-04

Il [confronto sintetico finito](qualification-compact-wire-experiment.md#confronto-reale-concluso-e-superato--2026-10-04) supera le soglie del 20% in entrambe le coppie: token di output −48,6/−51,0%, durata nativa di produzione −51,7/−55,5%; quattro risposte riesaminate favorevolmente sui criteri fissati. Si elimina output ridondante già vincolato alla fonte, mantenendo quattro fatti finali. Totali e primo JSON sono riportati separatamente e non dimostrano una riduzione del testo accettato nel browser.

La [integrazione selettiva](qualification-compact-wire-production.md) conserva il motore protetto, nessun retry, validatori indipendenti e rilettura della nota. Restano una installazione verificata di due file sul Mac e una singola sintesi reale nel browser, con recupero delle metriche native già raccolte dalla stessa inferenza. Non avviare un'altra serie A/B, altre prove CPU o voce prima di questo collaudo.


## Adozione compatta collaudata in produzione — 2026-10-04

Installazione di due file con backup e avvio Mac riusciti. Una sola sintesi reale sul percorso della nota scelta: completata/accettata e quattro punti riesaminati favorevolmente, testo nell’interfaccia a 26381 ms. Il lettore delle metriche recupera le fasi della stessa richiesta senza inferenza o lettura del vault: caricamento 5078,324 ms, contesto 11901,419 ms, produzione 9329,722 ms per 67 token, prompt 668 e cache dichiarata zero; totale backend 26376,82 ms. [Esito e limiti](qualification-compact-wire-production.md#collaudo-reale-concluso-e-superato--2026-10-04). Il precedente riferimento reale era circa 45,29 s: differenza osservata, non una garanzia statistica o causale universale.

Il task è chiuso: soglie del confronto sintetico finito superate, adozione protetta, 178 controlli pertinenti già passati e caso reale favorevole. Nessuna ripetizione ulteriore per chiudere questa modifica. Il contesto è ora la fase singola più costosa dell’osservazione, seguito dalla produzione e dal caricamento; questi dati orientano un eventuale task distinto sull’intera pipeline, senza saltare alla voce o dichiarare apprendimento automatico già attivo. Non pubblicare note, screenshot, ID o storico Terminale.

## Task distinto sul contesto: prova preparata — 2026-10-04

Andrea autorizza il punto 1 della roadmap. La [prova delle istruzioni specializzate](qualification-context-prompt-experiment.md) cambia soltanto il messaggio system del percorso compatto delle qualifiche: stessi passaggi e schema nativo, stessi quattro fatti finali e validatori. Quattro richieste sintetiche in ordine opposto, soglie fissate prima della raccolta su token di input e prefill senza cache, revisione del significato separata. 18 controlli nuovi e 178 regressioni passati; confronto Mac ancora da eseguire, nessun guadagno misurato o modifica della produzione. Il collaudo precedente resta chiuso.

## Esito del contesto e isolamento del prefill — 2026-10-04

La [serie Mac finita](qualification-context-prompt-experiment.md#esito-mac-della-serie-finita--2026-10-04) conserva il verdetto della soglia originale non superata: quattro risposte corrette e circa 29% di token in meno, ma cache nonzero e 161 token nuovi in entrambe le varianti del confronto avversariale. Nessuna adozione o ripetizione della serie. La [diagnosi distinta di due richieste con prefissi isolati](qualification-prefill-isolation-diagnostic.md) verifica il prefill quasi interamente nuovo senza unload, warm-up o perdita di informazioni. Protocollo e limiti della cache fissati prima dei nuovi dati; raccolta Mac ancora da eseguire. Non certifica beneficio con cache calda o latenza UI. Il task contesto rimane aperto; voce e altri moduli non vengono avviati.


## Istruzioni specializzate: adozione preparata — 2026-10-04

La [nuova diagnosi conclusa](qualification-prefill-isolation-diagnostic.md#diagnosi-mac-conclusa--2026-10-04) supera i criteri stabiliti prima della raccolta: 715 → 520 token nuovi (−27,273%), 10626,631 → 7906,994 ms di prefill (−25,593%), copertura 100%/99,4264%, due risposte riesaminate favorevolmente. Il vecchio test conserva il mancato superamento per cache. Nessuna serie va ripetuta.

La [adozione selettiva](qualification-context-production.md) cambia soltanto le istruzioni system per qualifiche della nota scelta: 1631 → 824 caratteri, passaggi e schema identici, validazione della risposta invariata, nessun prefisso diagnostico in produzione. 236 controlli pertinenti passati. Restano installazione di un file sul Mac e una sintesi reale con quattro fatti e tempi osservati; caricamento, contesto e produzione vanno letti dalla stessa richiesta senza un nuovo benchmark. Il risultato non certifica cache calda o latenza UI. Memoria, voce e altri moduli restano futuri.
