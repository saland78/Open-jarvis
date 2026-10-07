# Qualifica completa nel percorso Note Obsidian

Stato al 2026-10-04: **aggiornamento installato, compilazione completa sul Mac e collaudo della nota reale superati**. La revisione del significato conferma i quattro fatti selezionati e la frase corrente completa con le indicazioni di consultazione. Esito circoscritto al caso e al formato riconosciuto; nessuna verifica esterna o garanzia su altre sintesi. Questo difetto è chiuso nel caso collaudato; il prossimo task riguarda la latenza, senza perdere informazioni o controlli.

## Comportamento previsto

Nel percorso **Sintesi della nota**, per la convenzione KPI riconosciuta, il programma ricava dal passaggio originale la frase corrente completa: predicato, qualifica, ambito limitato alla nota e consultazione di dashboard/report con periodo, titolo e marketplace. Quella frase è un campo letterale, vincolato con const nello schema nativo prima della generazione e verificato nuovamente dopo. Gli altri tre record restano prosa del modello. Non si aggiungono o riparano parole dopo una generazione e non si effettua un secondo tentativo automatico.

[note_facts.py](../../scripts/andrea/note_facts.py) usa [qualification_sentence_guard.py](../../scripts/andrea/qualification_sentence_guard.py). Da qualification_clause_guard.py viene riusata soltanto la verifica del passaggio originale, della sua unicità e degli intervalli. Il percorso che proteggeva solo il prefisso non viene adottato.

La risposta identifica la frase riportata dalla fonte e distingue gli altri punti sintetizzati. Le descrizioni della pagina e il footer indicano le stesse origini. Le date delle qualifiche restano associate alla fonte; non si deducono anni dalla data del file. L'uguaglianza letterale non certifica la verità della nota o il significato di tutti gli altri record.

Prima di accettare il JSON rimane la rilettura completa della nota: contenuto, stato, origine del vault e data del file devono coincidere con la lettura iniziale. Nota cambiata, eliminata, resa inattiva o vault scollegato: risposta rifiutata. Restano controlli su numeri, date, fonte, completezza dello stream e gestione di timeout, cancellazione e richiesta concorrente.

Formulazioni di qualifica o consultazione non riconosciute si fermano prima dell'inferenza, senza essere completate per ipotesi. Il profilo del libro conserva schema e prompt precedenti; la modifica riguarda soltanto le qualifiche nel formato riconosciuto. Non è una sintesi universalmente libera o un addestramento del modello.

## Aggiornamento verificato

[update_qualification_sentence.py](../../scripts/andrea/update_qualification_sentence.py), **8890 byte**, SHA-256 **c605637ade074cddcfacb0d05e24be9c94432ae3b64ce517c5f7d0526bb46569**.

Scarica esattamente quattro file dal commit immutabile [ef604a5ef4a57cf12568ec8d4e792fd997136add](https://github.com/saland78/Open-jarvis/commit/ef604a5ef4a57cf12568ec8d4e792fd997136add):

| File | SHA-256 del nuovo sorgente | Condizione locale |
| --- | --- | --- |
| scripts/andrea/qualification_clause_guard.py | ad01e5192b19fc4bad068a0cdc288d9889fa0166eb2db6720283887910559757 | Assente oppure già identico |
| scripts/andrea/qualification_sentence_guard.py | 976e22ad3ba6671011cc63c0d18ae21a39e4647d4ad698454b70db983b943866 | Assente oppure già identico |
| scripts/andrea/note_facts.py | b2524d94ccbc7ab15e9d21e67ed91433cf6a37bedfe395aa6e27cbd46ea52ee7 | Hash precedente e07f8b87a63a46a4488cdc50a679fa9bb39a5c0c5f71101417b364e816d6a399 oppure già identico |
| frontend/src/pages/AndreaNotesPage.tsx | 5ece8d59a03a870cce6bce7cded885aa6a8d5b3db755389fbb1518b11fedc43c | Hash precedente 579a6218566a03737527c8c330b8cd29e653e088da0627ce92e805029132dc55 oppure già identico |

Verifica anche gli otto componenti immutati elencati in CHECKS, inclusi runtime, vault, engine Ollama, contratto, adattatore, streaming e prompt compatto. Non sovrascrive modifiche locali incompatibili, file mancanti previsti, collegamenti simbolici o collisioni con helper diversi.

Tutti i download, hash e controlli della sintassi Python terminano prima di applicare il primo file. Richiede porta 8008 libera e la mantiene riservata durante la transazione. Crea un backup locale; sostituzioni atomiche dei singoli file e ripristino dei precedenti in caso di interruzione o errore. I due helper nuovi vengono rimossi durante un rollback se prima non esistevano. Non termina processi.

Nessuna modifica a note, database, profilo, .env, specifiche delle dipendenze, modello, budget o Jarvis originale. La modifica del testo della pagina richiede ricompilazione dell'interfaccia: Avvia-OpenJarvis.command già rileva l'hash dei sorgenti. Nessun pacchetto o servizio vocale aggiunto.

## Verifica di sviluppo

**148 controlli Python e 12 controlli dell'interfaccia superati**, su note sintetiche e trasporto simulato. Coperti percorso ASGI della nota scelta, schema nativo con frase completa, provenienza e righe, convenzione KDP, rifiuto della continuazione incompleta osservata, fonti modificate durante la generazione, numeri/date estranei, note non supportate, interruzione e richieste concorrenti. Il risultato rimane pending_review quando un altro record supera controlli formali ma altera il significato: questi controlli non sono un oracolo semantico.

Gli undici test del nuovo aggiornatore usano i quattro payload effettivi e una cartella sintetica: successo con backup e ripetizione identica, quarto download corrotto prima di applicare qualsiasi file, file locali incompatibili, porta occupata, collegamenti, fonte mancante, sintassi invalida, modifiche durante il download e quarto replace interrotto dopo la sostituzione del bridge. Verificato ripristino del bridge precedente, rimozione dei nuovi helper e conservazione delle sentinelle di note, dati e configurazione.

I probe storici conservano i propri hash e i test usano gli archivi esatti delle rispettive versioni. Nessun criterio della precedente prova negativa viene rilassato o riclassificato.

Build **Vite/PWA completata**. Il compilatore TypeScript 7 nativo qui si arresta prima del controllo del codice perché readlink /proc/self/exe non è disponibile. Il comando combinato npm run build non viene dichiarato superato; la compilazione completa sul Mac rimane da verificare al riavvio. Non sono stati sostituiti compilatore o dipendenze del progetto.

Consultati prima dell'integrazione branch, PR #1 draft e [test structured output upstream](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_structured_output.py). Riusato il passaggio dello schema JSON completo nell'engine Ollama. Consultati convertitore e test const di llama.cpp b10969 dichiarato da Ollama v0.34.2, già riportati nel [rapporto della candidata](qualification-sentence-fix.md). Questa consultazione non è esecuzione delle suite upstream complete.

## Procedura del collaudo Mac ora concluso

Il collaudo è stato eseguito per un passaggio alla volta, dopo il risultato precedente. Procedura di riferimento:

1. Nella finestra **OpenJarvis**, Control+C e ritorno del prompt. Lasciare **Controlli** aperta. Non fermare altri progetti.
2. In **Controlli**, scaricare lo script dal commit pubblicato e verificare lo SHA-256 indicato prima di eseguirlo. Non assumere che sia già scaricato.
3. Eseguirlo con il Python della cartella OpenJarvis esistente, verificando messaggio finale e percorso del backup.
4. Nella finestra **OpenJarvis**, avviare con Avvia-OpenJarvis.command; attendere compilazione e avvio sulla porta 8008, quindi lasciare aperta la finestra.
5. Nel browser su http://127.0.0.1:8008, aprire **Data Sources → Note Obsidian**. Se la pagina conserva una versione vecchia, ricaricare completamente dopo il riavvio. Conservare il vault già configurato in sola lettura.
6. Cercare **KPI self-publishing**, identificare la nota KPI nella cartella dei numeri del self-publishing e premere **Sintesi della nota** su quel risultato. Il pulsante della nota scelta segue il percorso corretto di questa modifica.
7. Confrontare risposta e passaggi originali: conteggio dichiarato, variabilità per periodo, qualifica corrente limitata alla nota con consultazione completa, assenza storica distinta e date originali. La frase letterale deve essere identificata; gli altri punti non devono inventare zero, importi o verifiche esterne. Confermare che il trasporto termina e la sintesi non è rifiutata.

Se fallisce questo riscontro, conservare il risultato e la categoria del difetto, analizzare prima di qualsiasi altra modifica. Nessun retry per trasformare una prova negativa in successo e nessun passaggio a latenza, voce o altri moduli fino alla chiusura verificata.

Il [rapporto filtrato della singola prova sintetica Mac](qualification-sentence-fix-mac-2026-10-04.json) dimostra solo quel caso. Non sostituisce il collaudo della nota reale, non verifica dashboard KDP e non attesta verità esterne. PR #1 rimane draft, nessun merge a main.



## Chiusura verificata sulla nota reale — 2026-10-04

Installazione a quattro file con backup confermata dall'output dello script. La successiva compilazione **tsc -b && vite build** è terminata sul Mac, con bundle e PWA generati; il limite di /proc/self/exe del precedente ambiente di sviluppo non si è verificato sul Mac. Il browser mostra la pagina locale aggiornata e il percorso della nota scelta.

Una richiesta **Sintesi della nota** conclusa: controlli tecnici accettati, risposta e passaggi originali forniti per revisione. Tutti i quattro criteri di contenuto corrispondono ai passaggi selezionati: conteggio dichiarato, variabilità per periodo, qualifica corrente completa con ambito e consultazione, assenza storica distinta. Conservate le rispettive date originali e le citazioni. Nessuno zero, importo, aggiornamento economico o controllo della dashboard inventato. La frase corrente è identificata come testo della fonte e gli altri record come sintesi del modello.

**Test superato nel caso osservato**, con revisione manuale del significato. Il verdetto automatico pending_review non viene promosso a verifica semantica universale. Il [rapporto filtrato](qualification-sentence-production-mac-2026-10-04.json) conserva solo categorie, versioni e durate. Nessun testo della nota, screenshot, storico del Terminale, database, profilo o configurazione privata pubblicato.

Primo contenuto ricevuto dal browser e fine dello streaming: **45288 ms**. Primo e ultimo aggiornamento della risposta nell'interfaccia: **45290 ms**. Backend: recupero della nota **5 ms**, primo frammento JSON non mostrato **23685 ms**, generazione completa **45274 ms**, controlli **4 ms**, primo testo accettato **45285 ms**, totale **45286 ms**. Gli orologi di browser e backend non vengono sommati; il primo aggiornamento UI non misura l'esatto momento in cui lo schermo disegna il testo. La sintesi viene trattenuta fino ai controlli e questo spiega la coincidenza fra primo contenuto ricevuto e fine del trasporto; non significa una generazione istantanea.

Le fasi native di caricamento, valutazione del contesto, cache e produzione dei token non sono disponibili in questo screenshot. Non si attribuisce la durata a una di esse né si dichiara un miglioramento rispetto a prove diverse. Una sola osservazione reale non è una stima del percentile o una garanzia di latenza stabile.

Per chiudere questo difetto nel caso collaudato **non serve un'altra richiesta**. La prova precedente con consultazione omessa rimane fallita. Il nuovo task è ridurre la latenza mantenendo gli stessi fatti, qualifiche, date, provenienze e controlli: valutare separatamente informazioni già disponibili dalla fonte e prosa da generare, con una candidata delimitata e criteri fissati prima della prova. Non ripetere il vecchio esperimento di stile o cambiare modello e thread senza un'ipotesi nuova e verificabile.

Nessun nuovo test del modello o modifica runtime per registrare questa chiusura. Riconsultati i test structured output upstream al riferimento già verificato a0df94cd93756047c724d803662bc671618b10d4; la loro consultazione non equivale all'esecuzione completa o alla verifica dei dati esterni. PR #1 sempre draft, nessun merge.
