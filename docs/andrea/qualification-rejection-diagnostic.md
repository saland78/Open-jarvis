# Diagnosi di un rifiuto delle qualifiche: una sola richiesta sintetica

Stato al 2026-10-04 (Europe/Rome): preparata e verificata in sviluppo; nuova richiesta reale non ancora eseguita. Nessuna modifica alla produzione e nessun problema reale dichiarato risolto.

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

## Passaggio Mac

Lasciare il Terminale OpenJarvis in esecuzione e Controlli aperto. Non installare nulla nel progetto e non arrestare il server. Scaricare il solo diagnostico da un commit preciso, verificare l'hash e poi, in un passaggio successivo, eseguirlo con il Python del progetto:

```bash
"/Users/mac/Desktop/Documenti/OpenJarvis-Andrea/.venv/bin/python" /tmp/OpenJarvis-diagnose-qualification-rejection.py "/Users/mac/Desktop/Documenti/OpenJarvis-Andrea"
```

La guida attende il risultato di ogni piccolo passaggio. La richiesta reale resta da eseguire. PR #1 draft non unita e Jarvis originale intatto.
