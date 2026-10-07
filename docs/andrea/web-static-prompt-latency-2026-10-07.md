# Consolidare il contesto delle sintesi web

La latenza resta aperta. Il confronto CPU batch 128/512 è chiuso senza adozione:
128 non ha superato le soglie e due risposte asyncio avevano un predicato non
supportato dal proprio passaggio. Quei risultati restano invariati.

## Costo individuato e modifica proposta

La preparazione v9 accumula istruzioni sovrapposte da diversi adattatori. Nei
casi del programma, il sistema contiene 3.100 caratteri per asyncio, 2.156 per
la regola CSV e 1.985 per il prezzo non documentato. La nuova variante usa un
unico contratto di 1.349 caratteri, identico fra pagine e domande. Non è una
misura di token o secondi: il beneficio temporale deve essere misurato sul Mac.

Il limite di uno/due punti diventa `claimLimit` nei metadati, senza cambiare il
limite nello schema. La domanda resta ultima. Restano identici tutti i byte
della selezione originale, i riferimenti, gli altri valori dei metadati, lo
schema nativo e i validatori v9. Non si riduce arbitrariamente il contenuto
della pagina, non si eliminano condizioni e non si sostituisce la risposta con
una citazione. L'eventuale astensione deve essere generata dal modello.

Entrambe le varianti ricevono inoltre un controllo esplicito per il predicato
di controllo: la parola `controllare` non è accettata da un passaggio che parla
soltanto di esecuzione. Questo controllo rifiuta la risposta intera, conserva
il punto originale nella diagnostica e non cambia il suo riferimento. Non è
un classificatore generale di significato.

## Confronto unico, senza installazione

`scripts/andrea/web_prompt_compaction_probe.py` verifica il checker installato
e i suoi 24 fingerprint prima di importare il progetto. Richiede Ollama
0.35.1 con il modello CPU già usato. Legge due pagine pubbliche tramite la API
locale di OpenJarvis, poi esegue esattamente questa sequenza:

| Caso | Prima richiesta | Seconda richiesta |
|---|---|---|
| Due funzionalità asyncio | riferimento v9 | contratto statico |
| Regola di conversione csv.reader | contratto statico | riferimento v9 |
| Prezzo non documentato nell'estratto CSV | riferimento v9 | contratto statico |

Nessuna modifica al progetto installato, note, configurazione o dipendenze.
Stesse opzioni: temperatura 0,4; contesto 4096; output 512; batch 512; thread
automatici; thinking disattivato; keep-alive 15 minuti. Nessun retry, preload,
unload o riparazione di output. Il worker posseduto ha un limite di 95 secondi
per richiesta: in caso di blocco viene terminato solo quel worker. Il probe
non termina OpenJarvis o Ollama. La serie si ferma se il trasporto fallisce.

Un marcatore iniziale casuale isola la cache per rendere confrontabili i costi
del contesto. Questa prova non misura il beneficio di riuso del prefisso fisso.
Le osservazioni `pmset` riportano limiti CPU, non temperature o cause certe.
Ordine fisso e campione unico non permettono conclusioni causali generali.

Soglie stabilite prima delle misure:

- Identità di sorgente, preparazione di riferimento e schema in ogni coppia;
  massimo 8 token di contesto già in cache; metriche note e residenza CPU nota.
- Riduzione dei token in ingresso di almeno 10% nei due casi positivi e 5%
  nel caso di prezzo mancante.
- Riduzione del tempo di prefill di almeno 10% nei due casi positivi.
- Tempo totale della variante non oltre 5% peggiore in nessuno dei tre casi.
- Forma tecnica della variante: due punti asyncio, una regola CSV completa,
  astensione genuina per il prezzo. Una risposta vuota nei casi positivi fallisce.
- Revisione separata del significato di tutte le risposte. Per adottare la
  variante devono essere favorevoli tutti e tre i casi candidati; un riferimento
  sfavorevole resta registrato e non viene riparato o dichiarato favorevole.
- Anche un confronto favorevole richiede successivo collaudo del percorso
  installato. `integrationAllowed` resta falso nel report del probe.

Il tempo previsto è 4–8 minuti; limite complessivo approssimativo circa 11
minuti, incluso il recupero iniziale. Non usare contemporaneamente altre chat
o sintesi con Ollama. OpenJarvis resta acceso per leggere le pagine pubbliche.
Il risultato è scritto solo dove il comando esterno reindirizza l'output.

## Validazione svolta qui

88 test pertinenti superati: nuovo contratto e invarianti, controllo dei due
errori reali di predicato, rifiuti originari CSV/fonti/frasi incomplete,
trasporto/deadline, fingerprint, nessun retry e soglie non confuse con qualità.
I test di trasporto usano risposte simulate: nessuna inferenza sul Mac è stata
eseguita da questa sessione. Non è un risultato di latenza già ottenuto.

Riferimenti consultati per questo task:

- [OpenJarvis: test degli output strutturati](https://github.com/open-jarvis/OpenJarvis/blob/main/tests/engine/test_structured_output.py)
- [Ollama: output strutturati e validazione](https://docs.ollama.com/capabilities/structured-outputs)
- [llama.cpp: backend e compilazione](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)

L'approccio mantiene schema e validazione distinti dal giudizio di significato.
Non si cambiano backend, modelli o hardware sulla base di risultati di altri
computer. Per questo task non è richiesta una nuova installazione del motore.

## Risultato effettivo sul Mac: confronto non superato

Il report allegato il 7 ottobre è conservato integralmente, limitatamente al
JSON di questa prova, in `web-static-prompt-mac-2026-10-07.json`. La cronologia
del Terminale e gli altri esperimenti non fanno parte della pubblicazione.
La comparazione è stata ricalcolata dai sei risultati originali e coincide
con il report: tutti i trasporti completati, tutte le coppie confrontabili,
soglie numeriche complessive non superate e forma tecnica candidata non superata.

| Caso | Tempo v9 | Tempo contratto statico | Token v9 → statico | Esito numerico |
|---|---:|---:|---:|---|
| Due funzionalità asyncio | 55,002 s | 51,860 s | 1862 → 1497 | fallito: prefill 35,793 → 35,806 s |
| Conversione CSV | 32,990 s | 27,822 s | 1076 → 906 | superato: prefill −20,533%, totale −15,666% |
| Prezzo non documentato | 51,288 s | 62,172 s | 2368 → 2233 | fallito: totale +21,221% |

Il contesto in token è più corto in tutti e tre i casi; il risparmio non si
traduce in un miglioramento uniforme dei tempi. La variante asyncio supera
la soglia sui token ma non quella sul prefill. Il prezzo non documentato
resta un'astensione genuina, ma impiega circa 10,9 secondi in più.

Revisione manuale: quattro risposte favorevoli e due sfavorevoli. Entrambe le
risposte asyncio contengono un'aggiunta non sostenuta dal proprio passaggio:

- V9: il passaggio 18 documenta `running subprocesses`; il secondo punto
  afferma invece controllo dei sottoprocessi e aggiunge una relazione generale
  fra segnali OS, networking e comunicazione. Il controllo supplementare
  rifiuta l'intera risposta, senza cambiare fonte o predicato.
- Contratto statico: il passaggio 11 dice soltanto `control subprocesses`;
  il secondo punto aggiunge esecuzione di comandi esterni in modo asincrono.
  Il rifiuto originale `technical_term_missing_from_passage` resta conservato;
  non si elimina il punto né lo si modifica per far superare il caso.

Le due regole CSV conservano comportamento predefinito, eccezione e campo di
applicazione. I due prezzi mancanti sono `claims` vuoti prodotti dal modello.
La variante candidata ha quindi due casi semanticamente favorevoli su tre,
insufficienti per l'adozione. `pending_review` nel report automatico resta
inalterato; la revisione manuale è un campo distinto.

Decisione: nessuna installazione del contratto statico, nessun cambio del
batch, nessuna nuova generazione. Questo confronto è chiuso senza successo
e non viene ripetuto per cercare un risultato favorevole. La latenza resta
aperta; il precedente collaudo installato non diventa una garanzia universale.

I sei campioni riportano `sizeVram: 0`. Durante le richieste il limite
`CPU_Speed_Limit` scende fino a 60–68 in vari campioni. È un limite operativo
riportato dal sistema, non una temperatura misurata né la prova di una causa
termica esclusiva. Il costo di prefill è ancora predominante. Prima di
un'eventuale prova di backend locale accelerato occorrono GPU, VRAM, supporto
Metal e versione macOS effettivi; questi dati non sono nel report ricevuto.

La documentazione ufficiale di llama.cpp descrive il backend Metal su macOS
e Accelerate per il prefill CPU. L'issue upstream #19431 documenta una prova
su un altro Mac Intel/AMD: è un segnale di compatibilità da verificare, non
una promessa di velocità sul Mac di Andrea. Nessun backend è stato installato
o selezionato sulla base di questa issue.

- [llama.cpp: build e backend](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)
- [llama.cpp: segnalazione Intel/AMD Metal #19431](https://github.com/ggml-org/llama.cpp/issues/19431)
- [Ollama: supporto hardware](https://docs.ollama.com/gpu)

### Prossima lettura necessaria, senza altre inferenze

`scripts/andrea/mac_acceleration_inventory.py` legge una volta
`system_profiler -json SPDisplaysDataType`, con un limite di 20 secondi.
Stampa solo i campi della GPU: modello, vendor, VRAM e qualifiche Metal
riportate dal sistema. Aggiunge versione macOS, architettura e presenza dei
comandi git/cmake/clang; la presenza non dimostra che la compilazione funzioni.
Non riporta nomi, seriali o identificativi dei monitor, né l'ambiente del
processo. Non legge il vault o i file del modello e non contatta Ollama.

OpenJarvis può restare acceso durante questa lettura. Non occorre interrompere
il server o premere Command+R. Il risultato non stabilisce ancora compatibilità
o velocità di un nuovo backend e non installa nulla. Sette test del filtro e
del timeout sono superati, insieme ai 30 del confronto statico. Nessuna nuova
generazione è stata eseguita durante la revisione del risultato allegato.
