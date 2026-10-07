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
