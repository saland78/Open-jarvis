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


## Istruzioni specializzate collaudate in produzione — 2026-10-04

[Adozione installata e chiusa](qualification-context-production.md#collaudo-reale-concluso-e-superato--2026-10-04): un file con backup, avvio Mac, sintesi reale accettata e revisione manuale favorevole dei quattro fatti selezionati, frase corrente completa, qualifiche, date e citazioni. 236 controlli pertinenti passati. Il [lettore numerico](qualification-context-production-mac-2026-10-04.json) conserva le fasi della stessa richiesta senza ulteriori inferenze o lettura del vault: caricamento 5585,045 ms, contesto 8473,515 ms, generazione 5365,669 ms per 53 token, prompt 475 e cache zero. Totale backend 19488,63 ms.

Browser: contenuto 19518 ms, aggiornamento 19521 ms, **scheda osservata in secondo piano**. Escludere questo campione dai confronti UI in primo piano; non attribuire il beneficio del test sintetico al primo testo del browser. Esiti e limite registrati, senza una nuova prova per chiudere l’ambito attuale. Il vecchio confronto confuso dalla cache resta non superato; la diagnosi distinta quasi senza cache mantiene i criteri e il risultato propri. Il modulo successivo pianificato è memoria/correzioni; non attivato. Ulteriori confronti UI o pipeline audio richiedono progetto e protocollo propri.


## Riuso del contesto web collaudato in produzione — 2026-10-05

La [modifica di un solo file](web-prefix-reuse-2026-10-05.md#installed-mac-check-completed--2026-10-05)
è installata con backup e supera la revisione dei tre casi originali attraverso
OpenJarvis: due funzionalità asyncio fedeli ai passaggi, conversione CSV con
condizione e qualifica dei campi, astensione sul prezzo non documentato. Restano
distinti controlli automatici e revisione del significato; nessuna precedente
prova fallita viene trasformata in un successo. 298 regressioni pertinenti passate.

La domanda successiva sul medesimo estratto richiede 3591,521 ms, con 2364 token
di contesto riutilizzati su 2395. Le prime due sintesi richiedono 46690,960 e
50259,793 ms: il prefill nativo occupa 29916,533 e 36879,466 ms, la generazione
9307,990 e 13128,526 ms. Primo caricamento 7355,740 ms. Letture delle pagine
364/652 ms; disegno del browser non misurato. Questi tempi non vanno sommati tra
orologi diversi. Il guadagno osservato riguarda il riuso della pagina, non tutte
le richieste o la voce.

Questo task di riuso è chiuso nel suo ambito. La priorità residua della latenza
web è il costo del contesto alla prima richiesta, da trattare con protocollo e
collaudo distinti mantenendo le stesse informazioni, qualifiche e controlli.
Nessun nuovo benchmark o modulo è stato avviato per questa chiusura.

## Riduzione del contesto della prima sintesi web — prova distinta preparata

Andrea autorizza il miglioramento successivo della latenza. La
[prova delle istruzioni compatte](web-short-instructions-experiment-2026-10-05.md)
riduce soltanto il messaggio system da 2202 a 1430 caratteri, conservando intero
estratto, schema, domanda, inventari e tutti i validatori installati. Confronto
finito di sei richieste sui tre casi originali, ordine opposto nei due confronti
di pagina, prefissi diagnostici isolati senza unload/warm-up, soglie fissate prima
dei dati su cache, token nuovi e prefill. 313 controlli pertinenti passati;
misure e revisione del modello sul Mac ancora da raccogliere. Nessuna modifica
della produzione o velocità dichiarata; il precedente task di riuso resta chiuso.

## Prima prova della latenza web non superata — correzione delle istruzioni

La [serie di sei richieste sul Mac](web-short-instructions-experiment-2026-10-05.md#mac-series-completed-original-gates-not-met--2026-10-05)
si completa con cache idonea. Prefill inferiore del 17,679%/16,711%, ma perdita
di I/O e IPC nella risposta compatta asyncio e riduzione dei token CSV dell’8,633%
sotto la soglia originale del 10%. Cinque risposte riesaminate favorevolmente;
nessuna adozione, soglia ridotta o ripetizione per cercare un successo.
La [revisione distinta di conservazione delle sigle](web-short-retention-experiment-2026-10-05.md)
rende esplicita la copia di tutte le sigle per numero, sceglie descrizioni anziché
il solo titolo e compatta il messaggio system a 1265 caratteri. Fonti, schema,
validatore, opzioni, tre casi originali, ordine, cache e soglie restano invariati;
333 controlli pertinenti passati. Le nuove risposte e i tempi del Mac restano
da raccogliere: il task latenza è aperto, gli altri moduli rimangono rinviati.

## Diagnosi del plurale e dell’ambito delle sigle — 2026-10-06

La [serie della conservazione esplicita](web-short-retention-experiment-2026-10-05.md#mac-collection-completed-still-not-an-adoption-pass--2026-10-06)
conserva I/O e IPC, ma incontra due falsi rifiuti nel programma: `event loops`
non riconosciuto come `event loop` e OS richiesto dal distinto elemento sui
segnali nello stesso catalogo. CSV supera il criterio token (10,074%) ma non
il prefill (8,539% sotto 10%); ripete inoltre la regola, generando 126 token
contro 84 e peggiorando il totale. Esito originale non superato, nessuna adozione.

La [nuova prova isolata](web-scoped-latency-experiment-2026-10-06.md) corregge
soltanto il plurale finito e l’ambito OS/segnali nel caso esplicito dei sottoprocessi,
conserva i controlli su I/O/IPC e gli altri limiti, richiede punti non ripetuti
con istruzioni di 1229 caratteri e output italiano. Stessi estratti, schema,
opzioni, domande, ordine e soglie; entrambe le varianti usano il validatore
corretto e mostrano separatamente anche il vecchio controllo installato.
353 regressioni passate; risposte e tempi del modello sul Mac ancora pendenti.
Il task di latenza resta aperto; gli altri moduli rimangono rinviati.

## Soglie di velocità superate, prova semantica ancora aperta — 2026-10-06

La [serie con correzioni finite](web-scoped-latency-experiment-2026-10-06.md#mac-collection-reviewed--speed-gates-met-semantic-adoption-failed)
supera le soglie originali per entrambi i confronti: token nuovi -20,456%/-14,069%,
prefill -10,922%/-10,100%. Cinque risposte hanno revisione favorevole, ma la sintesi
compatta asyncio aggiunge un comportamento citando soltanto un titolo. Il suo
controllo strutturale non rileva questa insufficienza: variante non adottata.
Il tempo di caricamento del primo caso spiega parte del suo guadagno totale;
non viene attribuito alla sola compattazione. Nessuna dichiarazione di velocità
universale, disegno del browser o completamento di tutti i collaudi.

La [correzione dei ruoli HTML](web-heading-latency-experiment-2026-10-06.md)
conserva i titoli nel contesto ma li esclude come prove autonome, sia nello schema
del modello sia nel controllo del programma, mantenendo il testo identico. Una
prova distinta ripete i sei casi originali senza retry e con le stesse soglie;
il riferimento installato rimane invariato. 383 regressioni pertinenti passate;
risposte e misure del Mac restano da raccogliere. Produzione invariata e altri
moduli rinviati fino alla chiusura del task di latenza e qualità.

## Titoli corretti; equivalenza I/O e tipo CSV da collaudare — 2026-10-06

La [serie con ruoli HTML completata](web-heading-latency-experiment-2026-10-06.md#mac-collection-reviewed--heading-fixed-termtype-fidelity-still-open)
non seleziona più il titolo come prova. Entrambe le coppie superano le soglie
originali: token nuovi -20,479%/-13,770%, prefill -17,234%/-10,022%, cache idonea.
Il caricamento di 4066,436 ms della prima richiesta spiega parte della differenza
totale asyncio e non viene attribuito alla compattazione. Quattro risposte hanno
revisione favorevole. Restano un falso rifiuto dell'equivalenza input/output–I/O
e l'imprecisione “numeri decimali” al posto del tipo float nella sintesi CSV.
Il rapporto originario resta non superato; nessuna adozione.

La [correzione finita dei termini e del tipo](web-type-latency-experiment-2026-10-06.md)
riconosce soltanto l'espansione standard di I/O nello stesso passaggio e rende
esplicito il tipo float nell'inventario derivato dalla regola CSV della fonte.
Un controllo aggiuntivo rifiuta un diverso tipo di risultato senza correggere
testi generati. Fonti complete, domanda, riferimento installato, trasporto,
opzioni, sei casi originali e soglie rimangono invariati; il rilevatore lessicale
non certifica il significato. 426 regressioni pertinenti passate. Restano da
raccogliere sei risposte e misure sul Mac per questa revisione distinta: il task
latenza e qualità rimane aperto, gli altri moduli restano rinviati.

## Prefill variabile e diagnosi delle risorse — 2026-10-06

La [serie della fedeltà del tipo completata](web-type-latency-experiment-2026-10-06.md#mac-collection-completed--original-latency-gates-not-met)
mantiene float in entrambe le sintesi CSV; cinque risposte hanno revisione
favorevole. La variante compatta asyncio aggiunge un'interfaccia non documentata
nel proprio passaggio. Le soglie originali non passano: token nuovi -20,551% e
-13,864%, ma prefill -4,175% e -0,328% contro il minimo del 10%. Cache idonea e
controlli formali completati non bastano. Nessuna adozione o soglia ridotta.

La velocità per token nuovo cambia tra le varianti; non è stata misurata la
causa. Le letture delle pagine richiedono meno di mezzo secondo, il prefill
31–56 secondi. Prima di un altro confronto del modello, la
[diagnosi in sola lettura](web-resource-diagnosis-2026-10-06.md) rileva CPU,
memoria, alimentazione, limiti termici dichiarati e stato Ollama senza inferenza,
warm-up, modifiche globali o lettura di dati personali. Uno snapshot attuale
non ricostruisce il carico della serie precedente; dati assenti restano sconosciuti.

Un candidato isolato conserva fonti e schema e rifiuta il meccanismo aggiunto
nel noto passaggio breve sui sottoprocessi, senza correggere il testo generato.
448 controlli pertinenti passati. Diagnosi Mac ancora da raccogliere; successiva
ottimizzazione da scegliere in base a quelle misure, mantenendo qualità e soglie.
Il task latenza resta aperto e gli altri moduli restano rinviati.

## Osservazione sotto inferenza da raccogliere — 2026-10-06

La diagnosi del Mac si è conclusa in 3006,43 ms con CPU libera per l'88,43%,
swap usato zero e limiti CPU riportati al 100. Nessun modello era caricato;
Ollama risulta 0.35.1. Il campione a riposo non determina il costo delle risorse
durante il precedente prefill, né prova una causa termica o una scelta errata
di thread/batch. Le soglie originali della serie restano non superate.

Il [profilo di una sola richiesta CSV](web-active-resource-profile-2026-10-06.md)
conserva il prompt di produzione, la domanda, fonti, schema e opzioni. Raccoglie
al massimo tre letture delle risorse durante il processo posseduto, con limite
complessivo di 95 s per quel processo e nessun retry o modifica a impostazioni
e servizi. I campioni precedenti al JSON non sono automaticamente misure della
sola fase di prefill. 466 controlli del programma superati; raccolta Mac da fare.
Il profilo guida la scelta della prossima ottimizzazione e non chiude il test
precedente. Il task latenza rimane aperto, gli altri moduli restano rinviati.

## Limiti CPU osservati; riduzione del contesto API da confrontare — 2026-10-06

Il profilo CSV è completato: 57,696 s lato client, con 39,745 s di prefill,
4,821 s di caricamento e 13,090 s di generazione dichiarati da Ollama.
La risposta conserva condizione, campi non quotati e tipo float; revisione
favorevole per questa sola risposta. Il limite CPU dichiarato passa da 100
a 64 e 62 durante la stessa richiesta. Swap zero; misura di temperatura,
frequenza effettiva e causalità non disponibile. Le query CPU a intervallo
scadono e il processo runner attuale non viene individuato: CPU server quasi
zero non significa inferenza inattiva. Il profilo non supera un confronto A/B.

La [riduzione del contesto per API nominate](web-complete-api-context-latency-2026-10-06.md)
adatta il budget e la provenienza dei passaggi consultati nei test OpenJarvis.
Istruzioni ridotte a 772 caratteri; per nomi qualificati presenti nella domanda
il modello riceve sezioni HTML intere, complete e con numeri originali. Le
domande generali mantengono l'estratto completo. La selezione è dichiarata:
fonti integrali conservate per controllo, contesto del modello eventualmente
parziale. Nessuna condizione tagliata per rispettare il budget; fallback
completo se la sezione è incompleta, troppo grande, ambigua o non allineata.

490 regressioni pertinenti passate. La prova distinta mantiene le sei domande
originali, ordine bilanciato, opzioni, controlli e soglie del 10% in ogni coppia
supportata. Le letture termiche sono leggere e non fanno scartare risultati;
nessuna attesa per raffreddamento, warm-up o retry. Risposte e tempi Mac da
raccogliere. Nessuna adozione o dichiarazione di riduzione già misurata.
Il task latenza e qualità resta aperto; gli altri moduli rimangono rinviati.

## Contesto API più veloce; due errori tecnici da correggere — 2026-10-06

La [serie Mac delle sei richieste](web-complete-api-context-mac-2026-10-06.json)
è completata senza retry: entrambe le coppie superano le soglie originali.
Token nuovi/prefill: asyncio −26,734%/−18,688%; CSV −68,307%/−67,946%.
La selezione CSV conserva tutta la definizione di `csv.reader` in 1481
caratteri; fonte completa e numeri dei passaggi restano disponibili per audit.

Il confronto complessivo non è superato. Due risposte compatte trasformano
`subprocesses` in generici processi e `unquoted` in campi non incapsulati;
la risposta CSV ripete inoltre la stessa conversione. I validatori rifiutano
correttamente i due errori. Le altre quattro risposte hanno revisione
favorevole. Nessun testo errato corretto dopo la generazione, soglia abbassata
o precedente report trasformato in successo; nessuna adozione.

La [correzione delle forme tecniche](web-canonical-term-latency-fix-2026-10-06.md)
mantiene la selezione completa e rende espliciti sottoprocessi e campi non
racchiusi tra virgolette. Una regola condizionata resta un unico punto;
un controllo ristretto, applicato a entrambe le varianti, rifiuta due
ripetizioni positive della medesima conversione CSV senza rimuoverle.
Istruzioni 990/1157 caratteri: leggermente più lavoro rispetto al candidato
fallito, ancora sotto i 2202 della produzione. Il nuovo effetto sui tempi
deve essere misurato, non dedotto da queste dimensioni.

496 controlli del programma superati, inclusi gli errori effettivi appena
raccolti. Nuova revisione isolata con gli stessi tre casi, sei richieste,
fonti, opzioni e soglie originali. Nessun warm-up, retry, cambiamento termico,
lettura di note personali o installazione. Restano nuove risposte e metriche
del Mac da raccogliere e verificare: latenza e qualità hanno priorità sugli
altri moduli. Nessun miglioramento universale o rendering browser certificato.

## Forme tecniche corrette; vincolo nativo per la singola regola — 2026-10-06

La [nuova serie Mac](web-canonical-term-mac-2026-10-06.json) è completata:
token nuovi/prefill −23,321%/−55,233% per asyncio e −66,025%/−69,533% per
CSV. Le traduzioni ora conservano sottoprocessi e campi non racchiusi tra
virgolette. Cinque risposte hanno revisione favorevole secondo il controllo
dei fatti effettivamente selezionati; la risposta CSV ripete la medesima
conversione e viene correttamente rifiutata. Il vecchio controllo installato
continua a segnalare OS nel punto asyncio che non seleziona i segnali: il
report conserva separatamente questo esito e la motivazione dell'ambito.
Il confronto complessivo resta non superato, senza adozione.

La [correzione della cardinalità](web-single-rule-cardinality-2026-10-06.md)
interviene prima della generazione. Un modulo distinto riconosce solo le
domande supportate sulla regola di conversione di `csv.reader`, verifica
una sola regola completa nella sezione originale e invia uno schema nativo
con al massimo un punto. Le condizioni restano nella stessa frase, con
lo spazio necessario a completarla. Domande generali, più fatti o API,
forme sconosciute e fonti ambigue conservano due punti. Nessuna risposta
precompilata, rimozione di frasi, taglio di parole o retry.

507 regressioni passate. Le sei domande, fonti, modello/opzioni e soglie
originali restano fisse. Solo la variante CSV riconosciuta cambia il limite
nativo: `[2, 2, 1, 2, 2, 2]` nei sei invii. Lo schema e il motivo sono
registrati, mentre la baseline installata rimane identica. Il rispetto
effettivo del vincolo e la fedeltà di tutti i fatti devono ancora essere
misurati con il modello sul Mac. Il programma non elimina un eccesso per
farlo passare: lo rifiuta e conserva il testo diagnostico. Qualità e latenza
restano il task aperto; gli altri moduli non vengono avviati.

## Regola CSV completa; precisione dei segnali OS — 2026-10-06

La [serie con limite nativo di un punto CSV](web-single-rule-cardinality-mac-2026-10-06.json)
completa le sei richieste e supera entrambe le coppie di soglie originali:
token nuovi/prefill −23,610%/−21,032% per asyncio e −65,929%/−72,821% per
CSV. La regola CSV è unica e conserva default, condizione, campi senza
virgolette e tipo float. Il difetto di duplicazione è risolto in questa prova.

Il report automatico resta accettato con revisione pendente. La revisione
separata trova cinque risposte fedeli e una non fedele: la seconda frase
asyncio trasforma la gestione dei segnali dell’OS in generica comunicazione
con l’OS. Il confronto completo non è superato e non viene adottato; il
report automatico originale e il testo del modello restano integri.

La [correzione della qualifica](web-signal-scope-latency-fix-2026-10-06.md)
lega il termine e il suo controllo al passaggio originale prima e dopo la
generazione. Non impone di menzionare i segnali quando il fatto selezionato
riguarda soltanto sottoprocessi. Il vincolo CSV riuscito, la selezione completa
e le soglie restano invariati. Istruzioni aggiuntive solo nei contesti che
documentano quella relazione; nessuna riparazione o seconda generazione.

519 regressioni passate, compreso l’errore effettivo accettato dai vecchi
controlli. La nuova serie Mac serve a verificare risposte e tempi dopo questa
correzione. La misura del disegno a schermo e un miglioramento statistico o
universale non sono certificati. Qualità e latenza restano l’unico task attivo.
