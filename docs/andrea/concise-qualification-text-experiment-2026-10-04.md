# Candidata di sintesi più concisa: confronto isolato

Stato al 2026-10-04 (Europe/Rome): quattro richieste reali completate sul Mac. **Candidata non adottata: soglia di prestazioni fallita.** Un riferimento del caso avversariale è rifiutato per unsupported_value_update; il suo JSON grezzo non è conservato. Nessuna modifica al runtime di produzione e nessun miglioramento prestazionale dichiarato.

## Problema e singola differenza candidata

Nel [confronto di riuso in produzione](production-native-phases.md), caricamento e valutazione del contesto scendono a costi millisecondi, mentre la produzione di 138 token richiede ancora circa 19,24 secondi. Questo motiva una prova della lunghezza della risposta, non un altro esperimento sui thread già concluso senza guadagni.

La candidata aggiunge una sola istruzione generica di stile al messaggio di sistema del percorso riconosciuto delle qualifiche datate: scegliere frasi essenziali preservando tutte le informazioni e i limiti del singolo passaggio, comprese le indicazioni di consultazione, ed emettere JSON su una riga senza spazi superflui fuori dalle stringhe. Non vengono fornite frasi attese o risposte esemplari al modello.

Messaggio utente, quattro fatti obbligatori, passaggi originali, schema JSON nativo completo, date, qualifiche, numeri e validatore sono identici fra riferimento e candidata. Il tetto resta 512 token: non viene ridotto per troncare la risposta. Modello Instruct, temperatura 0,4, contesto 4096, think=false e keep_alive=15m invariati. Il prompt dei libri e la sintesi generale non sono modificati.

Il precedente prompt globale più corto è rimasto un fallimento documentato. Questa prova non ne riclassifica l'esito e non adotta la candidata sulla base di sole citazioni o somiglianze di parole.

## Confronto finito: quattro richieste, due casi sintetici

Script autonomo temporaneo: [concise_qualification_text_probe.py](../../scripts/andrea/concise_qualification_text_probe.py). SHA-256: 6cbfecc754d8ab4fb46399d703e73effcd4bdd1a796994edd621e8fd37a9a975; 16931 byte.

Ordine fissato prima della raccolta:

1. Caso ordinario, messaggi di produzione.
2. Stesso caso ordinario, istruzione candidata.
3. Caso avversariale, istruzione candidata.
4. Stesso caso avversariale, messaggi di produzione.

Il caso ordinario contiene un conteggio dichiarato, variabilità per periodo, qualifica corrente non verificata nella nota con indicazioni di consultazione e assenza nella fotografia storica. Il secondo usa conteggio, date e predicato differenti, metadati irrilevanti e istruzioni ostili fuori dai passaggi pertinenti. Le fonti sono Markdown sintetico pubblico, non note personali.

La preparazione dei fatti e dei messaggi avviene con gli stessi moduli di produzione verificati tramite SHA-256. Otto sorgenti di riferimento sono controllati prima di eseguire moduli o inviare richieste: runtime, engine Ollama, contratto, adattatore Markdown, sintesi con qualifiche, stream strutturato, prompt delle qualifiche e bridge dei fatti. Runtime ed engine sono verificati ma non importati. Vengono eseguiti soltanto i moduli pubblici verificati necessari alla preparazione e validazione. File inattesi o symlink interrompono la prova prima della rete. Nessuna guardia di vecchi diagnostici viene rilassata.

La prova invia quattro POST direttamente a Ollama locale, non al percorso ASGI della UI. Non legge il vault, non usa connettori, strumenti, proxy o servizi esterni, non modifica sorgenti, database, profilo o dipendenze e non scrive report o bytecode. Nessun preload, unload, warm-up aggiuntivo o retry. Una prova fallita resta nel rapporto: gli altri casi prefissati proseguono senza sostituirla. Control+C conserva un rapporto parziale e ferma la serie.

Il processo Ollama è condiviso: durante la serie non usare altre chat/client. I prompt sintetici possono sostituire il contesto in cache; ciò non è una modifica globale persistente. Alla fine non è necessario reinstallare o ripristinare OpenJarvis: nessun suo file è stato modificato.

## Criteri prima della raccolta

Per ogni risposta:

- Mantiene il conteggio dichiarato e la variabilità per periodo, citando la fonte originale.
- Separa DATO NON VERIFICATO nell'aggiornamento da DATO ASSENTE nella fotografia storica, con le rispettive date.
- Limita le qualifiche alla nota e alla fotografia; non inventa zero, importi, aggiornamenti avvenuti o assenze nella dashboard.
- Mantiene le indicazioni di consultazione presenti nel passaggio; non esegue istruzioni nelle fonti e non inventa una verifica esterna.

Trasporto completo/stop e accettazione del medesimo contratto sono controlli tecnici separati dal significato. Una negazione semanticamente errata può passare il contratto: il test di sviluppo documenta esplicitamente quel limite e qualityVerdict resta pending_review. Le risposte sintetiche accettate e i passaggi originali vengono mostrati per revisione umana; testo grezzo rifiutato non viene presentato come risposta accettata.

Soglia esplorativa di prestazioni, fissata prima della raccolta: in ENTRAMBE le coppie, almeno 10% in meno di eval_count nativo e almeno 10% in meno di eval_duration nativa, con tutti e quattro i trasporti e contratti validi. Il confronto usa le quantità non arrotondate per la decisione; un arrotondamento visualizzato al 10% non fa passare una riduzione inferiore. Contatori mancanti, invalidi o zero impediscono la valutazione utile. Dati mancanti restano null, distinti da zero dichiarato.

Quattro richieste non costituiscono un benchmark statistico. Cambiano cache/caricamento fra prompt: primo JSON e totale diretto vengono conservati, ma non sono il criterio primario per il costo di produzione dei token. Nessun tempo viene chiamato latenza del browser, né il primo JSON viene chiamato risposta verificata. Le misure native sono millisecondi ottenuti dal frame finale Ollama; token/s non è calcolato dal numero di chunk.

Anche con soglia favorevole, decision resta not_adopted_requires_semantic_review_and_production_validation. L'adozione richiederebbe revisione favorevole di tutte le risposte, regressioni del percorso interessato e una verifica circoscritta su nota reale nella UI. Se la candidata perde informazioni o non offre un guadagno utile, chiudere il confronto mantenendo la produzione attuale, senza nuove varianti o ripetizioni per ottenere un campione favorevole.

## Verifica di sviluppo conclusa

15 controlli mirati passati: 12 nuovi e 3 regressioni della composizione del prompt di produzione. Comprendono quattro richieste NDJSON HTTP a un server Ollama simulato locale usando i moduli di produzione, stesso schema/payload/budget, ordine finito, nessuna scrittura o retry, fallimenti tecnici conservati, rifiuto di date/conteggi/qualifiche/predicati alterati, distinzione fra formato e significato, errori di trasporto, campi nativi invalidi/mancanti, interruzione, limiti di stream, deadline controllata fra letture, baseline incompatibile e symlink. Otto sorgenti locali confrontati byte per byte con quelli pubblicati nel branch verificato a5db0ca34dde7d104d3201bcc2de25be453ee793. Sintassi dello script verificata.

Nessun modello reale, browser o nota personale utilizzato nel contenitore. Nessun backend Rust completo o intera suite upstream eseguito per questa prova. Il socket ha timeout 90 secondi e la durata è controllata fra letture; non è una garanzia di scadenza esatta durante una lettura bloccata. Stream limitato a 4 MiB, singola riga 256 KiB e risposta generata 32000 caratteri; parsing rifiuta chiavi duplicate, tool call, contenuti non testuali e JSON troppo annidato.

Consultati per questo task [test_structured_output.py](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/tests/engine/test_structured_output.py) e [test_ollama_runtime_options.py](https://github.com/open-jarvis/OpenJarvis/blob/792131feb3948aca0b54a94e0344f6827ff3129d/tests/engine/test_ollama_runtime_options.py), oltre ai guard del fork e agli esiti dei prompt precedenti. Si conserva il formato JSON Schema nativo già usato: non si sostituisce con un semplice suggerimento di JSON. Consultazione distinta dall'esecuzione dei test upstream.

## Preparazione Mac precedente alla raccolta

Lasciare OpenJarvis in esecuzione nel suo Terminale. In Controlli scaricare lo script da un commit pubblicato preciso e verificarne l'hash prima di eseguirlo con il Python del progetto e la cartella del progetto come unico argomento. Non fermare o aggiornare il server. La guida procede con un solo piccolo passaggio per turno.

Dalla cartella del progetto, dopo la verifica del download:

```bash
.venv/bin/python /tmp/OpenJarvis-concise-qualification-probe.py "$PWD"
```

La raccolta descritta sopra è ora conclusa: non ripetere questa serie o introdurre nuove varianti per ottenere un campione favorevole. Lo storico del Terminale e i contenuti dell'allegato non sono pubblicati. PR #1 draft e non unita; Jarvis originale intatto.


## Chiusura sul Mac: obiettivo di velocità non superato

[Misure filtrate e categorie](concise-qualification-text-mac-2026-10-04.json). Tutti i quattro trasporti terminano con stop; tre contratti sono accettati e uno è rifiutato. Le seguenti durate sono produzione nativa dei token, non tempo del browser.

| Caso | Variante | Token generati | Produzione nativa, ms | Contratto |
|---|---|---:|---:|---|
| Ordinario | Produzione | 136 | 14836,539 | Accettato, significato da riesaminare |
| Ordinario | Concisa | 136 | 14962,566 | Accettato, significato da riesaminare |
| Avversariale | Concisa | 134 | 14808,403 | Accettato, significato da riesaminare |
| Avversariale | Produzione | 131 | 14373,091 | Rifiutato: unsupported_value_update |

Nella coppia ordinaria la riduzione dei token è 0% e quella della durata di produzione è -0,849%. Nella coppia avversariale sono rispettivamente -2,290% e -3,029%, oltre al contratto rifiutato del riferimento. La soglia già fissata del 10% per entrambe le quantità in entrambe le coppie non è raggiunta. Il totale inferiore della seconda richiesta ordinaria coincide con caricamento e cache differenti e non dimostra una decodifica più veloce. Nessuna stima statistica o generalizzazione da quattro richieste.

Le due risposte ordinarie accettate hanno lo stesso testo reso: conservano conteggio, variazione per periodo, etichette separate con date, indicazioni di consultazione e ambito nella nota/fotografia. Revisione favorevole limitata a questi criteri. Nel caso avversariale la candidata mantiene conteggio, date, etichette e consultazione, ma la parafrasi non conserva esplicitamente il predicato di persistenza «restano»: non si certifica equivalenza completa del significato. La candidata è comunque esclusa dal risultato prestazionale, senza modificare retroattivamente la soglia.

Il riferimento avversariale non può essere revisionato semanticamente: il raccoglitore scarta modelAnswer anche quando il contratto è rifiutato. Si conosce soltanto la categoria unsupported_value_update. L'ispezione del codice mostra che un predicato con «aggiornati» deve coincidere esattamente all'inizio di una riga della fonte; ad esempio, «sono» al posto di «restano» causa rifiuto. Questo è un esempio riprodotto in sviluppo, **non** una ricostruzione della frase reale ormai scartata. Non si assume un falso positivo e non si rilassa il controllo.

I collaudi favorevoli precedenti sul caso reale della nota scelta e sul riuso restano documentati nel loro ambito. Il nuovo rifiuto evidenzia un limite aggiuntivo: non dimostra che ogni sintesi sia corretta o accettata, né annulla le misure precedenti.

## Diagnosi successiva distinta, una sola richiesta

[Diagnostico del rifiuto](qualification-rejection-diagnostic.md): stessa fonte avversariale sintetica, messaggi di produzione e controlli invariati, conservando il JSON della nuova richiesta esclusivamente per analisi. Nessuna candidata di stile, correzione del testo o modifica del runtime. Un'eventuale accettazione del nuovo campione non riclassifica questa prova fallita e non recupera il JSON scartato. La diagnosi serve a ottenere evidenza della causa, non a scegliere una generazione favorevole.



## Chiusura della diagnosi distinta

La [singola nuova diagnosi](qualification-rejection-diagnostic.md#esito-reale-della-singola-richiesta) è completata. In questo campione il contratto accetta quattro record: il rifiuto originale non è riprodotto e la sua causa resta aperta perché il JSON precedente non è conservato. La nuova parafrasi omette il predicato esplicito di persistenza presente nella fonte: accettazione tecnica distinta dalla conservazione completa del significato.

Questa osservazione non cambia l'esito prestazionale negativo delle quattro richieste sopra e non adotta la candidata. Nessuna ulteriore ripetizione di questa serie. Il prossimo lavoro riguarda la preservazione del predicato e dell'ambito prima di altri confronti di velocità.
