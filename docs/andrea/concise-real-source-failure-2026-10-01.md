# Riassunto reale: criterio di qualità non superato — 2026-10-01

## Verdetto

Il controllo finale nell'interfaccia, dopo la modifica dello stile breve, **non è superato**. La sintesi introduce una data di validità a partire da una fotografia storica, senza che la fonte definisca una scadenza. Inoltre accosta valori aggiornati non verificati e dati storici assenti senza mantenere una distinzione temporale sufficiente.

La risposta cita la fonte attiva prevista e termina nell'interfaccia, ma presenza della citazione, brevità e completamento non rendono corretta la parafrasi. Screenshot, estratti e risposta personali non vengono pubblicati: questo documento registra soltanto il difetto tecnico osservato.

## Evidenze conservate

I sei casi sintetici con criteri invariati restano superati, come documentato in concise-quality-review-2026-10-01.md. Le misure in concise-timing-review-2026-10-01.md restano quelle osservate: totale mediano della sintesi 24,35 → 13,48 secondi. Nessun esito viene cancellato o riclassificato.

Questi risultati non approvano la modifica complessiva: i sei esempi non esercitavano la trasformazione di una fotografia storica in una scadenza. Il corpus reale rende visibile un limite distinto. Non è dimostrato che il solo stile breve abbia causato il difetto; è dimostrato che la versione proposta non soddisfa il criterio finale di qualità.

Il controllo è letto rispetto alla fonte, consultando nuovamente tests/evals/scorers/test_doc_qa.py upstream al commit c4da16e1ca3d21f4cc1905d4200063e564104f0f. La suite upstream completa non è dichiarata eseguita. Non si modifica una nota personale per adattarla a un errore del modello e non si ripete la stessa domanda fino a ottenere un risultato favorevole.

## Ripristino circoscritto

Il branch torna al runtime precedente alla guida di stile breve, SHA-256 fb30f0b3f179b73cd8976e706653c898fa4da9bfe5739ba0706dfbdef2895ff3. Le due prove di confine vengono adeguate al runtime ripristinato e continuano a verificare messaggi della chat, fonti complete, budget 512 e conservazione dello stream lungo con citazione finale.

restore_concise.py applica soltanto runtime.py e il relativo file di prove, da un commit fissato. Accetta esclusivamente le versioni previste, verifica hash, richiede porta 8008 libera e crea backup con rollback. La ricerca con estratti preparati dopo la selezione, già collaudata sul Mac, resta attiva. Conteggi diretti, modello, parametri, frontend, dati, dipendenze e Jarvis originale non vengono modificati.

Il ripristino è preparato in sviluppo; l'applicazione sul Mac resta da confermare. Non si dichiara che il runtime precedente elimini ogni possibile errore della sintesi libera.

## Direzione successiva

Prima di un nuovo intervento occorre aggiungere un caso sintetico preregistrato che distingua una data di fotografia da una scadenza e mantenga separati dati storici e correnti non verificati. La priorità è una rappresentazione e un controllo delle evidenze temporali verificabili; abbreviare ulteriormente il testo non costituisce una soluzione a questo difetto.

Il lavoro sul nuovo stile viene ritirato come impostazione attiva. Il collaudo complessivo di quella proposta rimane negativo. PR draft, senza unione a main; nessun dato esterno è verificato e non si dichiara apprendimento.
