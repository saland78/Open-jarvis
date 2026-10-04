# Diagnosi di un rifiuto delle qualifiche: una sola richiesta sintetica

Stato al 2026-10-04 (Europe/Rome): una richiesta reale completata sul Mac, JSON diagnostico disponibile e riesaminato. **Rifiuto precedente non riprodotto in questo campione; causa del rifiuto precedente non risolta.** Nessuna modifica alla produzione. Conservazione completa del predicato nella nuova parafrasi non certificata.

## Evidenza disponibile e limite del rapporto precedente

Il [confronto di testi più concisi](concise-qualification-text-experiment-2026-10-04.md) è chiuso senza adozione: non raggiunge le soglie prestazionali fissate. Il riferimento avversariale termina con stop ma è rifiutato per unsupported_value_update. Il vecchio raccoglitore scarta modelAnswer; il testo responsabile del rifiuto non è recuperabile da quel rapporto. Una causa concreta non può essere attribuita soltanto dalla categoria.

L'ispezione del controllo di produzione mostra che la frase contenente «aggiornati» è ammessa soltanto come predicato iniziale esatto sostenuto dalla fonte. In sviluppo si riproduce, ad esempio, un rifiuto quando la fonte usa «I valori aggiornati restano DATO NON VERIFICATO» e la generazione usa «I valori aggiornati sono DATO NON VERIFICATO». Non si conclude che quella sia stata la frase reale, né che ogni rifiuto della categoria sia un falso positivo. Le affermazioni verbali di aggiornamenti non documentati devono continuare a essere rifiutate.

## Raccolta mirata, senza una nuova candidata

[diagnose_qualification_rejection.py](../../scripts/andrea/diagnose_qualification_rejection.py), 6079 byte, SHA-256 f310ffbed2148e8a12caecc58d24b89af674baa84590d11c2b9aac867a5aaa0e.

Lo script riusa la copia temporanea già scaricata di concise_qualification_text_probe.py, verificata tramite SHA-256 6cbfecc754d8ab4fb46399d703e73effcd4bdd1a796994edd621e8fd37a9a975 prima di eseguirne qualunque codice. Riferimento immutabile: commit 7246999dc87cabc46ce5366d38941d0f894bc077. Percorso Mac predefinito della dipendenza: /tmp/OpenJarvis-concise-qualification-probe.py. Se manca, è collegata o ha contenuto diverso, fermarsi senza richieste; non scaricare o eseguire altro automaticamente. --probe-script permette un percorso assoluto esplicito alla medesima copia verificata. L'entry point del vecchio confronto non viene eseguito.

Si conservano tutti gli otto controlli SHA-256 sui sorgenti di produzione prima di caricare i moduli o usare la rete. Runtime e engine sono verificati ma non importati. I moduli necessari a preparazione e validazione sono quelli pubblici verificati; nessuna configurazione privata o nota viene letta.

Viene inviata una sola richiesta sul caso avversariale pubblico già definito, con gli stessi messaggi di produzione, schema JSON nativo completo e opzioni. Nessuna istruzione candidata aggiunta, nessun seed cambiato, nessun warm-up, unload o retry. Modello qwen3:4b-instruct-2507-q4_K_M, temperatura 0,4, num_ctx 4096, num_predict 512, think=false e keep_alive=15m. Chiamata diretta a 127.0.0.1:11434, proxy disattivati e redirect rifiutati. Il percorso server/browser non è misurato e i tempi non vengono chiamati latenza dell'interfaccia.

Il risultato mantiene:

- Contratto originale completo, categoria di rifiuto o accettazione tecnica e risposta resa soltanto se accettata dal contratto.
- JSON generato per diagnosi, anche se rifiutato o troncato; esplicitamente distinto da una risposta accettata. Errori del trasporto non espongono messaggi arbitrari; in tali casi il JSON è null.
- Per ciascun record datato, passaggio sintetico originale, frase generata e risultato del medesimo controllo unsupported_value_update. Questo controllo per record non stabilisce quale guardia completa sia fallita per prima e non certifica il significato.
- Quantità native valide dal frame finale e durate client distinte; contatori assenti restano null.
- Indicazione che l'esperimento prestazionale precedente rimane fallito, nessuna modifica adottata e revisione semantica ancora necessaria.

Non si riscrive il JSON, non si elimina «aggiornati», non si sostituisce un verbo, non si ritenta e non si rilassa il validatore. La fonte sintetica usa conteggi e date di esempio, non dati personali. Nessun file di progetto, nota, database, dipendenza o profilo viene modificato; niente report o bytecode scritti. Il contenuto diagnostico è stampato soltanto nel Terminale e non viene pubblicato automaticamente su GitHub.

Il processo Ollama è condiviso: evitare altre chat durante l'unica richiesta. I prompt sintetici possono sostituire il contesto in cache senza cambiare una configurazione globale persistente. Limiti del trasporto ereditati: timeout socket 90 secondi e durata controllata fra letture, senza garanzia di scadenza esatta durante letture bloccate; 4 MiB di stream, 256 KiB per riga e 32000 caratteri generati. Chiavi duplicate, tool call e contenuti non testuali sono rifiutati. Control+C interrompe senza un secondo tentativo.

## Criterio di chiusura della diagnosi

La diagnosi è informativa se fornisce il JSON di questo nuovo campione e consente di confrontare la frase con il passaggio originale. Se il rifiuto ricompare, verificare il record preciso e la categoria del contratto prima di proporre una correzione. Se non ricompare, riportare che non è stato riprodotto in questo singolo campione: non dichiarare corretto il rifiuto precedente o risolta la sua causa. In nessun caso riaprire il confronto prestazionale per convertirlo in un successo.

Qualunque correzione futura deve mantenere il rifiuto di aggiornamenti realmente non documentati, date indovinate, qualifiche fuse, numeri estranei e istruzioni nelle fonti. Non adottare un controllo più permissivo per una frase reale sconosciuta. Citazioni e formato non certificano l'equivalenza del significato o una verifica di dashboard esterne.

## Verifica di sviluppo

21 controlli mirati passati: sei nuovi del diagnostico e quindici regressioni del raccoglitore/composizione del prompt. Verificati una sola POST con payload di produzione invariato, conservazione esatta del JSON rifiutato, identificazione del record con predicato non coincidente, nessuna riparazione o scrittura, esiti precedenti non riclassificati, negazione semanticamente errata ancora pending_review, JSON invalido/duplicato, altre guardie distinte dall'ispezione del predicato, troncamento/EOF/tool call/errori di trasporto, interruzione e dipendenza/baseline inattese prima della rete. Incluso un vero stream NDJSON HTTP contro un server Ollama simulato locale: non inferenza reale.

Consultati in questo task tests/engine/test_structured_output.py e tests/engine/test_ollama_runtime_options.py dell'upstream al commit 792131feb3948aca0b54a94e0344f6827ff3129d. Riutilizzati i principi di payload/schema nativo e opzioni esplicite, oltre al trasporto e ai moduli del fork già verificati. Consultazione distinta dall'esecuzione dell'intera suite upstream. Nessun modello reale, vault personale, browser o backend Rust completo eseguito nel contenitore.

## Passaggio Mac eseguito — non ripetere

Lasciare il Terminale OpenJarvis in esecuzione e Controlli aperto. Non installare nulla nel progetto e non arrestare il server. Scaricare il solo diagnostico da un commit preciso, verificare l'hash e poi, in un passaggio successivo, eseguirlo con il Python del progetto:

```bash
"/Users/mac/Desktop/Documenti/OpenJarvis-Andrea/.venv/bin/python" /tmp/OpenJarvis-diagnose-qualification-rejection.py "/Users/mac/Desktop/Documenti/OpenJarvis-Andrea"
```

La guida ha ricevuto il rapporto della singola richiesta. La serie è conclusa: non ripetere per cercare un nuovo campione favorevole. PR #1 draft non unita e Jarvis originale intatto.


## Esito reale della singola richiesta

[Misure filtrate e categorie della diagnosi](qualification-rejection-diagnostic-mac-2026-10-04.json). Una richiesta tentata e completata con stop, zero retry, nessuna lettura del vault o modifica di produzione. Contratto valid_structure_pending_semantic_review, quattro fatti coperti secondo i controlli tecnici, nessuna categoria di rifiuto. Non è un certificato di accuratezza semantica.

| Quantità | Osservazione |
|---|---:|
| Primo frammento JSON al client diretto | 16075,498 ms |
| Totale al client diretto | 32696,042 ms |
| Caricamento nativo | 3816,075 ms |
| Valutazione del contesto nativa | 12225,209 ms |
| Produzione dei token nativa | 16620,572 ms |
| Totale nativo | 32691,377 ms |
| Token del contesto | 799 |
| Token del contesto dichiarati in cache | 0 |
| Token generati | 134 |
| Token/s dalla fase nativa di produzione | 8,062 |

Queste misure descrivono la nuova chiamata diretta, non la UI o il server ASGI. Caricamento e cache sono diversi dalla precedente richiesta avversariale: non usare il totale come confronto di ottimizzazione né attribuire una causa specifica all'assenza di cache. Il primo frammento JSON non è testo già validato e visibile al browser.

### Confronto della frase con la fonte sintetica

La fonte del record corrente contiene il predicato «I valori aggiornati restano DATO NON VERIFICATO soltanto in questa nota» con indicazioni di consultazione. Il modello genera «I valori sono DATO NON VERIFICATO» seguito dalle indicazioni di consultazione. Nella frase generata non compare «aggiornati»: il controllo unsupported_value_update ritorna false quando non trova quella famiglia di parole. L'ispezione riporta false sia per F3 sia per F4, coerentemente con il codice.

Il conteggio dichiarato, la variabilità per periodo, le due etichette, le indicazioni di consultazione e le date di contesto nella risposta resa sono mantenuti. Le date del contesto sono assegnate e rese attraverso lo schema e il programma, non prova che il modello abbia appreso a conservarle autonomamente. La delimitazione alla nota e alla fotografia compare nei prefissi resi dal programma. Non risultano importi estranei o verifiche esterne affermate.

La parafrasi non conserva esplicitamente «restano», che esprime persistenza, né l'aggettivo presente nella fonte. La conservazione completa di questo predicato non è dimostrata dalla semplice accettazione del formato e delle etichette. La diagnosi individua quindi un limite osservabile di preservazione dell'informazione; non ricostruisce la frase che aveva causato il rifiuto precedente.

### Decisione di chiusura

- Diagnosi informativa conclusa: JSON del nuovo campione acquisito e confrontato con i passaggi.
- Rifiuto originale non riprodotto, causa non risolta; il vecchio JSON scartato resta indisponibile.
- Esperimento di stile precedente ancora fallito e candidata non adottata. Nessuna nuova richiesta o variante per riclassificarlo.
- Nessuna modifica di produzione, modello, budget, validatore o note; prove favorevoli precedenti restano circoscritte ai loro casi.
- Testo grezzo diagnostico e storico personale del Terminale esclusi dal rapporto pubblicato.

## Prossimo intervento definito: conservazione del predicato e dell'ambito

Prima di altre prove di velocità, progettare una correzione circoscritta che mantenga il predicato e l'ambito della qualifica anche quando il modello omette la parola «aggiornati». Non usare quella omissione come dimostrazione che il rifiuto precedente sia risolto e non rendere il guard più permissivo per frasi ignote.

Valutare un contratto che separi elementi protetti sostenuti dalla fonte e prosa generata, mantenendo trasparente quale componente copia/assegna il contesto e quale parafrasa. La scelta non è ancora implementata o adottata. Conservare i fatti originali e la provenienza; rifiutare aggiornamenti realmente non documentati, negazioni, qualifiche fuse, ambito esteso alla dashboard e istruzioni ostili. Fissare prima i criteri di regressione e riesaminare il significato, distinguendo sintesi del modello, testo protetto e passaggi copiati.

La riduzione successiva del JSON ridondante può riguardare metadati già legati alla fonte dal programma, senza troncare risposte o confondere una copia con apprendimento del modello. Riduzione dei token e latenza richiederanno una verifica reale distinta; nessun guadagno dichiarato da questo rapporto.

Per questa chiusura verificati branch, PR draft e upstream main al commit 792131feb3948aca0b54a94e0344f6827ff3129d; riconsultati i controlli sul formato del payload in tests/engine/test_structured_output.py e il guard del fork. Nessuna nuova modifica al codice: non ripetuti i 21 controlli di sviluppo già conclusi. Consultazione dei test upstream distinta dalla loro esecuzione completa.
