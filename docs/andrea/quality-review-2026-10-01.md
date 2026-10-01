# Esito del collaudo locale dei riassunti — 2026-10-01

## Verifica del percorso nel browser superata

Dopo l'installazione di update_retrieval.py dal commit fbc7dd36ca4fdcf0697398935c84135edeead23f (cinque file fissati al commit sorgente e540a871c2f42d0a8d3a47e573fd18e9dd96eb47), l'installazione e il riavvio sul Mac sono riusciti.

Ripetendo la stessa domanda naturale, la nota KPI nominata è ora il primo risultato: 320 risultati, 364 note controllate, 3304 ms. La risposta riporta letteralmente il campo richiesto, cita N1 e mostra la fonte attiva con le righe originali. Il testo corrisponde all'estratto aggiornato; non aggiunge vendite, royalty o informazioni dalle trascrizioni. È il percorso dei campi espliciti, senza sintesi generativa. Non sono stati consultati sistemi esterni.

**Sono superati i sei casi sintetici fissati e il controllo di ricerca e risposta sulle note reali per questa domanda.** Collegamento e lettura delle note erano già verificati. I risultati certificano questi percorsi e criteri, non l'intero significato del vault o ogni risposta libera del modello. Fonti con lo stesso titolo restano possibili evidenze discordanti; i dati esterni non sono certificati dalla citazione.

Il miglioramento osservato è la pertinenza della prima fonte. La durata della ricerca, 3304 ms contro 3189 ms della precedente esecuzione, non dimostra un miglioramento della latenza; sono singole rilevazioni. La durata della risposta o del primo testo nel browser non è stata cronometrata.

Resta la raccolta separata dei tempi già prevista: tre richieste di chat breve e tre sintesi sulla nota KPI, usando il client di controllo. Include le misure della ricerca/preparazione e del percorso di generazione, non la futura pipeline audio. I contenuti del vault e della risposta non vengono conservati nel risultato timings. Il modello non viene cambiato o scaricato dalla memoria. Lo stato freddo/caldo non viene dedotto.

Nessuno screenshot, testo della nota, titolo privato di libro o report KDP viene pubblicato con questa registrazione.

## Verifica precedente nel browser: selezione delle fonti non superata

Dopo i sei casi sintetici corretti, una domanda naturale sui libri pubblicati nei KPI dell'attività ha prodotto 320 risultati, 364 note controllate e 3189 ms. Nello screenshot locale i primi due risultati erano la scheda di un singolo libro e una trascrizione di formazione, non la nota KPI nominata. Questo è un limite del recupero delle fonti, che gli estratti sintetici già forniti non esercitavano. Nessuna risposta con quelle fonti è stata approvata e la fase complessiva sul vault reale non è conclusa.

La correzione di sviluppo riconosce il titolo completo di una nota dentro una domanda, dà precedenza a quel gruppo prima del taglio dei risultati e lo usa per le fonti della risposta. Mantiene fonti distinte con lo stesso titolo, il rifiuto degli stati esclusi e della scansione parziale. Una fonte nominata esclusa non viene sostituita da una trascrizione incidentale. Il riconoscimento è lessicale, non una comprensione generale di tutte le domande o una certificazione dei dati. Non contiene percorsi personali o conteggi corretti fissati nel codice.

Sono coperti la forma esplicita dei campi con «sono», anche in Markdown, e il rifiuto delle unità scalate dopo marcatori di formattazione. Le righe restano citazioni testuali.

La regressione è stata riprodotta prima della modifica con un corpus sintetico comprendente quindici trascrizioni. Dopo la correzione sono passate 50 verifiche mirate: 21 sull'adattatore usando il parser upstream isolato, 12 sulle evidenze, 8 sulle misure, 3 sul client, 6 sulla transazione di aggiornamento. È coperto il flusso ASGI che legge file sintetici reali, seleziona la nota e riporta il conteggio senza inferenza. Consultati i test upstream di recupero, BM25 e Obsidian; la suite completa Rust non è stata eseguita.

La correzione non è ancora installata sul Mac e il nuovo controllo nell'interfaccia con il vault reale resta pendente. I sei casi sintetici della sezione seguente conservano il loro esito positivo; non sostituiscono questa prova del recupero delle note. Lo screenshot, titoli privati e testi delle note non sono inclusi nel repository.

## Collaudo sintetico: sei casi superati dopo il controllo dei campi espliciti

Revisione del collaudo eseguito sul Mac il 2026-10-01 dopo l'installazione di update_evidence.py dal commit 0c0dda8441e6dbfa42b69e7c672b1e981f4d1c56. I sette file sorgenti sono fissati al commit 6e9d83435fdeb95c1d5d6970dcb6997b44005d8a. L'installazione ha completato verifiche e backup; la compilazione dell'interfaccia sul Mac è riuscita in 1,55 secondi.

**La suite finita di sei casi è superata nella revisione umana del significato.** Il raccoglitore conserva correttamente qualityVerdict: pending_review: non effettua da solo questa valutazione. Tutti gli stream sono completi, non troncati e con citazioni formalmente valide.

Dataset e criteri non sono cambiati. È cambiato il percorso sottoposto a prova: le richieste usano ora il backend delle note con estratti sintetici forniti esplicitamente. I casi explicit, conflict e opinion riportano campi riconosciuti senza inferenza; unknown, historical e no_answer usano il modello. È un risultato del sistema nel suo insieme, non una prova che il modello abbia imparato o che la sua accuratezza generale sia migliorata.

| Caso | Modalità osservata | Revisione del significato |
|---|---|---|
| explicit | explicit_fields; inferenceUsed: false | Riporta letteralmente due libri, Italia e Stati Uniti e la fotografia al 2026-08-20, citando N1. |
| unknown | model_synthesis; inferenceUsed: true | Limita il dato non verificato agli estratti; non deduce zero, l'assenza dei dati esterni o un report mai scaricato. |
| conflict | explicit_fields; inferenceUsed: false | Segnala 0 e 2, cita entrambe le fonti e non sceglie un conteggio in base alla data del file o alla separazione delle schede. |
| historical | model_synthesis; inferenceUsed: true | Descrive il problema del codice a barre come risolto e limita l'assenza di problemi successivi agli estratti. |
| opinion | explicit_fields; inferenceUsed: false | Riporta soltanto due copie nel settembre 2026 come campo dichiarato nella nota, citando N1; non introduce percentuali o contenuti estranei. |
| no_answer | model_synthesis; inferenceUsed: true | Le royalty di ottobre non risultano negli estratti; nessun importo inventato né estensione del limite alle fonti esterne. |

Le due copie del caso opinion sono **un dato sintetico**. Nessun report personale, dashboard KDP o vendita reale è stato verificato da questa suite.

### Tempi osservati in questa esecuzione

| Caso | Primo testo client, ms | Totale client, ms | Inferenza |
|---|---:|---:|---|
| explicit | 24,42 | 24,50 | No |
| unknown | 17101,58 | 24431,97 | Sì |
| conflict | 2,38 | 2,45 | No |
| historical | 2250,63 | 14378,91 | Sì |
| opinion | 3,51 | 3,62 | No |
| no_answer | 1670,04 | 4714,72 | Sì |

Per i tre casi senza modello generationMs e generationFirstTextMs sono null, come previsto; answerMode e inferenceUsed distinguono i percorsi. I tempi sono misurati nel Terminale. Gli estratti sono forniti, quindi i valori non includono una scansione del vault o il rendering del browser. Non si confrontano i millisecondi delle risposte senza inferenza con il TTFT del modello. L'attesa di 17,10 secondi del caso unknown è osservata, ma la causa e lo stato freddo/caldo non sono determinati.

### Ambito della conclusione e lavoro rimasto

Il risultato certifica soltanto questi sei esempi e i criteri fissati. Il modulo riconosce un insieme dichiarato di campi e può mostrare valori discordanti; non risolve automaticamente tutti i conflitti del vault e non garantisce ogni sintesi libera. Citare una nota non dimostra che il suo contenuto sia vero o aggiornato.

Restano il controllo di questo nuovo percorso nell'interfaccia con note reali e la raccolta separata di tempi chat/risposte sulle note. Il collaudo del browser per questa modifica non è ancora documentato. Non è autorizzata alcuna unione della PR draft a main.

Per questa revisione sono stati consultati nuovamente scripts/andrea/quality_cases.json al commit installato e tests/evals/scorers/test_doc_qa.py dell'upstream. Le verifiche dei fatti e delle citazioni rimangono distinte dalla revisione del significato. Non si dichiara eseguita l'intera suite upstream.

## Esito precedente conservato

La sezione seguente documenta l'esito negativo prima dell'introduzione di evidence.py. Il difetto osservato spiega la correzione; non viene rimosso o riclassificato retroattivamente.

## Stato del collaudo precedente

La suite di accuratezza **non è superata**. Il prompt installato proviene dal commit 30a32f82c559345c1a960627bc5d961975e6cef1; l'aggiornatore è pubblicato nel commit 648799093aff63b1dfcbe3f28f4ace7d02cbd220.

Sei casi sintetici sono stati eseguiti sul Mac con qwen3:4b-instruct-2507-q4_K_M. Usano il prompt di produzione e gli estratti immutati di scripts/andrea/quality_cases.json. Non leggono il vault: il valore di due copie nel caso opinion è un dato sintetico, non una verifica delle vendite personali.

| Caso | Criteri fissati | Revisione del significato |
|---|---|---|
| explicit | Rispettati | Due libri, data e citazione corretti. |
| unknown | Rispettati | Dato non verificato limitato all'estratto; nessuno zero né indisponibilità dei dati esterni. |
| conflict | Non rispettati | Riporta 0 e 2 e cita entrambe le fonti, ma nega il conflitto perché le schede sono separate. La fonte non fornisce questa giustificazione. |
| historical | Rispettati | Descrive la risoluzione e limita l'assenza di problemi successivi agli estratti. Confermato anche nel controllo del singolo caso. |
| opinion | Rispettati, con un difetto aggiuntivo | Riporta due copie e settembre 2026, non introduce il 90% e attribuisce la valutazione. Tuttavia trasforma l'abbandono del self-publishing in abbandono di corsi; la frase finale sui contesti esterni è inoltre ambigua. |
| no_answer | Rispettati | Royalty di ottobre non determinabili dagli estratti, senza inventare importi. |

I criteri non sono stati modificati dopo le risposte. Cinque casi rispettano i criteri specifici originali, ma questo non cancella il contenuto non sostenuto dalla fonte nel caso opinion. La revisione complessiva resta negativa.

Tutti i sei stream sono completi, non troncati e superano i controlli formali sulle citazioni. Questo esito di protocollo non certifica l'accuratezza; qualityVerdict rimane pending_review nel raccoglitore.

## Misure raccolte

Primo testo al client: 1,35–2,07 secondi. Totale: 4,06–13,14 secondi. Sono durate di queste sei risposte diverse, misurate nel Terminale; non includono ricerca nel vault o rendering del browser. Stato freddo/caldo non determinato. Non sono un confronto fra chat e riassunto sulle note né una misura della futura pipeline vocale.

## Consultazione dell'upstream

Riferimento esaminato: open-jarvis/OpenJarvis, commit c4da16e1ca3d21f4cc1905d4200063e564104f0f.

- examples/doc_qa/doc_qa.py indicizza documenti e invoca Jarvis.ask con contesto.
- src/openjarvis/evals/scorers/doc_qa.py verifica corrispondenze di parole, presenza delle citazioni e una checklist opzionale. La corrispondenza di parole può approvare affermazioni semanticamente false; un modello giudice non è una prova indipendente della verità.

Il collegamento a documenti e l'esistenza dei test upstream non risolvono automaticamente i difetti osservati del modello locale.

## Vincoli emersi dal collaudo precedente

Non ripetere la suite invariata per cercare una risposta favorevole. Non dichiarare il collaudo concluso. Non cambiare criteri, conteggi o modello per nascondere il fallimento.

Prima di un'altra installazione occorre progettare una risposta basata su evidenze controllabili: distinguere fatti espliciti, conflitti irrisolti, opinioni e dati non verificati, conservando citazioni ed estratti. I controlli automatici sulle forme o sui numeri devono dichiarare il proprio ambito; non possono essere presentati come una verifica generale del significato.

La parte già collaudata di collegamento, ricerca e lettura del vault rimane utile. La sintesi libera del modello non è ancora affidabile in tutti questi casi. Jarvis originale e configurazione locale restano separati. Nessuna nota personale o esportazione del vault è inclusa in questo documento.
