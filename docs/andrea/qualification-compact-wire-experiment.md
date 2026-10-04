# Prova della sintesi con meno campi generati

Stato al 2026-10-04: **preparata e collaudata con trasporto simulato; nessuna inferenza reale eseguita e nessuna adozione in produzione**. Il precedente difetto della frase corrente rimane chiuso per il caso reale già riesaminato. Questa prova riguarda la latenza; non riapre quel collaudo né riclassifica gli esperimenti precedenti falliti.

## Problema e candidata

La produzione attuale richiede al modello quattro record JSON. Il testo del record F3 è già una frase letterale obbligatoria, vincolata tramite `const`; le date dei contesti sono anch'esse già ricavate dalle intestazioni originali. Farli emettere al modello richiede comunque output. La candidata evita tale rigenerazione senza omettere quelle informazioni nella risposta.

| Elemento della risposta finale | Produzione attuale | Candidata isolata |
|---|---|---|
| F1, conteggio dei libri | Sintesi del modello, controllata | Stessa responsabilità e controlli |
| F2, variabilità per periodo | Sintesi del modello, controllata | Stessa responsabilità e controlli |
| F3, qualifica corrente e consultazione completa | Frase originale emessa dal modello con `const`, verificata identica | Frase originale copiata dal programma dal passaggio già comprovato prima dell'inferenza |
| F4, qualifica storica | Sintesi del modello, controllata | Stessa responsabilità e controlli |
| Date corrente e storica | Campi vincolati nel JSON del modello | Valori ricavati dalle stesse intestazioni originali prima dell'inferenza |
| Citazioni, passaggi e righe | Programma e prove originali | Identici |

Il trasporto candidato chiede esclusivamente `{"F1":"…","F2":"…","F4":"…"}`. Rifiuta chiavi duplicate, mancanti o aggiuntive, il vecchio envelope, stringhe vuote, tipi diversi e output eccessivo. Ricompone esplicitamente le due origini in quattro record, mantenendo ogni stringa del modello identica, e passa il risultato ai validatori di produzione invariati, compresa la verifica della frase corrente completa. La ricomposizione non riempie F1/F2/F4 mancanti e non ripara numeri, qualifiche o date errate del modello. La frase F3 e le date sono dichiarate come contenuti della fonte, non come apprendimento o capacità generativa dimostrata.

Il programma ricalcola il piano con l'estrattore di produzione, controlla il testo completo della fonte, i metadati della candidata e i passaggi originali. Un test ha rilevato una mutazione fuori dai passaggi selezionati: il vincolo sul testo completo è stato aggiunto prima della pubblicazione. Per un'eventuale integrazione resta necessario mantenere anche la rilettura della nota e l'identità del vault già presenti nel percorso ASGI. La prova qui usa soltanto Markdown sintetico pubblico e non legge il vault.

## Ipotesi misurabile

Per i due casi sintetici, i messaggi passano da 3198 a 2288 caratteri e da 3223 a 2289; lo schema nativo serializzato passa rispettivamente da 1126/1138 a 277 caratteri. Sono lunghezze di caratteri, **non misure dei token o della velocità**. Il miglioramento sul Mac resta da misurare.

La richiesta reale appena chiusa ha impiegato circa 45,29 s fino all'aggiornamento UI, con recupero della nota scelta di circa 5 ms. La schermata non conteneva le fasi native complete: non si attribuiscono quei 45 s a caricamento, prefill o decoding senza leggere i contatori della stessa richiesta. I tempi del backend e del browser non vanno sommati.

## Ordine e criteri fissati prima della misura

Prima leggere `read_native_phases.py`: un GET delle misure in RAM della richiesta di produzione già eseguita, nessuna inferenza. Il risultato contiene solo numeri/stati filtrati. Se il server è stato riavviato o la richiesta non è più nelle ultime osservazioni, segnala il limite; non genera automaticamente un nuovo campione.

Poi, soltanto quando utile alla diagnosi, eseguire `qualification_compact_wire_probe.py` una volta. Lo script è autonomo: incorpora la candidata verificata, controlla undici file della produzione installata prima di caricarli e prima/dopo ogni richiesta. Non serve installare la candidata. Nessun download di modello, cambio dipendenze, unload, warm-up forzato, retry o modifica ai file del progetto.

Le richieste previste sono **quattro al massimo**, sequenziali:

1. Caso ordinario, produzione.
2. Stesso caso ordinario, candidata.
3. Caso avversariale, candidata.
4. Stesso caso avversariale, produzione.

Un errore di trasporto o un rifiuto tecnico interrompe le richieste restanti. I risultati già prodotti rimangono nel rapporto. Il secondo caso usa conteggio, date e predicato diversi, metadati e istruzioni estranee non autorizzanti; nessuna nota personale entra nella prova. Entrambe le varianti usano `qwen3:4b-instruct-2507-q4_K_M`, temperatura 0,4, contesto 4096, massimo 512 token, `think=false`, `keep_alive=15m`, thread automatici e limite di 90 s per richiesta. Non utilizzare contemporaneamente chat o sintesi nel browser.

La soglia esplorativa richiede, **in entrambe le coppie**, almeno il 20% in meno di token nativi di output **e** di durata nativa di decoding, con trasporto completo e quattro fatti tecnicamente accettati. Contatori mancanti, coppie incomplete o una sola coppia favorevole non superano la soglia. Il modello continua a dover conservare conteggio, variabilità, qualifica storica e ambito; la frase corrente deve includere periodo, titolo e marketplace, con date e citazioni corrette. La revisione del significato di tutti i punti è separata e obbligatoria prima di considerare un'adozione.

Il rapporto distingue caricamento, contesto, cache e produzione; l'ordine opposto riduce una fonte di distorsione ma non fornisce significatività statistica. Totale e primo frammento JSON non dimostrano un miglioramento del testo accettato nel browser. Non si nascondono eventuali regressioni del contesto dietro la soglia di decoding. Nessuna adozione automatica: per integrare servono un esito favorevole di qualità e prestazioni, mantenimento dei confini ASGI e una verifica della latenza sul percorso reale. Fallback e messaggi di origine devono rimanere espliciti.

## Verifiche di sviluppo concluse

- 16 nuovi test passati: copertura dei quattro fatti, frasi e date dalle fonti, offset e righe, nessuna riparazione del testo, omissioni/chiavi duplicate, numeri e date inventati, mutazioni di fonte/metadati/schema/prompt, varianti dei predicati e formulazione KDP, rifiuto dei libri, limiti e completamento, confronto con soglie per entrambe le coppie, hash e ripristino del registro moduli, lettura senza inferenza.
- 148 regressioni precedenti passate nello stesso lavoro: ponte di produzione, frase completa, prove precedenti, adattatori e stream. Il primo insieme contava 163 test; l'ultimo test HTTP aggiunto è passato nel successivo insieme dei 16 nuovi.
- Collaudo HTTP locale con simulatore: quattro vere richieste loopback, schema e impostazioni corretti, frame terminali e metriche native. Questi tempi sintetici non sono un benchmark.
- Nessun frontend, runtime installato, modello o dipendenza modificato; non è necessaria una nuova build per eseguire la prova. Nessuna suite upstream completa o inferenza reale eseguita in questo ambiente.

I test conservano un controesempio con negazione nel punto sulla variabilità che può superare i soli controlli tecnici: resta `pending_review`. La candidata non è un validatore semantico generale e non promette che ogni sintesi sia corretta.

## Consultazione GitHub e upstream

Baseline del fork: `32aabf8f3bd2cc0314b282ce85da73984624f9fc`, branch `feature/andrea-local-profile`, PR #1 draft e non unita. Undici sorgenti riletti e confrontati integralmente con GitHub. Consultati nuovamente [tests/engine/test_structured_output.py](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_structured_output.py) upstream: invio del formato al motore e separazione dal risultato. Si riusa il percorso Ollama esistente con schema nativo e validazione indipendente; non si installa indiscriminatamente il progetto upstream.

Il trasporto HTTP, i limiti e i casi sintetici sono copiati senza modifiche dal precedente `concise_qualification_text_probe.py`; la candidata di stile fallita non viene applicata. Il nuovo loader verifica la produzione corrente, inclusi i due guard della frase installati, senza cambiare gli hash delle prove storiche. Jarvis originale resta indipendente.

## Lettura della richiesta esistente conclusa — 2026-10-04

Il lettore delle fasi native ha restituito le misure della richiesta accettata già completata: totale backend 45285,52 ms, primo testo accettato 45285,07 ms, recupero 4,54 ms e controlli 3,53 ms. Sono coerenti con la schermata della prova reale precedente. Nessuna nuova inferenza o lettura del vault effettuata dal lettore; la qualità resta quella già riesaminata, non una valutazione eseguita dal lettore delle metriche.

Ollama dichiara totale 45253,159 ms, caricamento 5332,582 ms, contesto 18294,775 ms e produzione 21589,931 ms. Contatori: 951 token di prompt, cache zero, 142 token generati, 6,577 token/s in produzione. Il primo frammento JSON nel backend arriva a 23684,59 ms e rimane separato dal testo accettato. Questi contatori spiegano il costo osservato in quella richiesta; non stabiliscono il motivo del mancato riuso della cache, non rendono universali quei tempi e non vanno sommati alle misure del browser.

Il contesto e la generazione rappresentano entrambi costi consistenti. Il confronto preparato è pertinente perché riduce i messaggi di contesto e il trasporto generato preservando i quattro fatti finali. Restano da misurare token e durata effettivi della candidata, con gli stessi criteri già fissati; nessuna nuova prova A/B o adozione effettuata. Il caricamento è riportato separatamente e non viene eliminato con unload o richieste di riscaldamento.

[Snapshot numerico filtrato](qualification-compact-wire-native-baseline-2026-10-04.json): nessuna nota, percorso personale, screenshot, ID richiesta o cronologia del Terminale pubblicati. Lo script di confronto autonomo è pubblicato al commit `2e8ac5f8a975ec1dfecb75944c0d5273540dc6aa`, SHA-256 `72bd2b65bfceb69dcfbb596bd53b575b016945cf0081642ee7e23ea020e8dfc0`. Primo passo successivo: scaricarlo e verificare il checksum; l'esecuzione delle quattro richieste segue dopo la verifica. OpenJarvis resta acceso; non è un aggiornamento dei sorgenti installati.
