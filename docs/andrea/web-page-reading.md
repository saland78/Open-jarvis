# Lettura esplicita e sintesi di una pagina

Stato: prima versione installata e collaudo circoscritto sul Mac concluso il 2026-10-04 (Europe/Rome), come indicato sotto. Miglioramenti alla visibilità, estrazione e misure preparati, ancora da installare e collaudare sul Mac. Nessuna garanzia generale di correttezza semantica o prestazionale.

## Flusso

Nella pagina Ricerca web, ogni risultato offre «Leggi pagina in Jarvis». Questa azione contatta soltanto il sito selezionato e i suoi eventuali reindirizzamenti. Il testo estratto, URL finale, data di consultazione, durata e limitazione dell'estratto sono mostrati prima dell'inferenza. «Sintetizza questa pagina» è una seconda azione esplicita, con una domanda modificabile.

La sintesi usa il modello locale configurato e soltanto domanda ed estratto. Non aggiunge note, memoria dichiarata, conversazioni, altri risultati o conoscenze recuperate da altri servizi. Una sola generazione; nessun retry, acquisto, configurazione di credenziali o cambio di fornitore.

## Download e isolamento

- HTTPS sulla porta 443, senza credenziali nell'URL, proxy o cookie. Nessun JavaScript eseguito.
- DNS verificato su tutti gli indirizzi restituiti, con rifiuto di destinazioni private, link-local, multicast, metadata e indirizzi di transizione. DNS non risolto: nessun download.
- Connessione a un solo indirizzo numerico verificato; TLS autentica il nome originale. Nessuna seconda risoluzione del nome per la connessione, nessun tentativo su un indirizzo alternativo.
- Massimo due reindirizzamenti, ognuno verificato prima della nuova connessione.
- Processo separato; 25 secondi complessivi comprendono DNS e download. Timeout/interruzione terminano e attendono il processo.
- Corpo massimo 1 MiB, solo HTML o testo semplice, nessuna compressione. PDF e altri tipi non sono interpretati.
- Testo massimo 6000 caratteri; script, navigazione e alcuni elementi non pertinenti esclusi. L'estrazione non riproduce il rendering del browser: CSS e pagine dinamiche possono influenzare ciò che è effettivamente visibile.
- Ultimo estratto soltanto in RAM per cinque minuti, con token opaco. Una nuova lettura sostituisce la precedente; un riavvio cancella la disponibilità. Nessun salvataggio della pagina o della domanda in file applicativi.
- POST soltanto dall'origine locale; blocco condiviso con chat e altre operazioni. La sintesi accetta il token della lettura, non testo sostitutivo inviato dal browser.

## Inferenza e limiti della verifica

Al massimo due coppie di sintesi/passaggio originale. Il JSON viene bufferizzato; non viene mostrato durante la generazione. Limite 90 secondi e impostazioni del modello locale già applicate dal runtime (512 token massimi). Uno stream incompleto o con strumenti è rifiutato.

Controlli: forma del JSON, limiti di lunghezza, passaggio presente letteralmente nell'estratto con sola normalizzazione degli spazi, assenza di nuove cifre non presenti nel passaggio e assenza di citazioni o URL aggiunti dal modello. Il programma associa [W1] alla pagina realmente letta.

Questi controlli non dimostrano implicazione logica, corretta attribuzione, pertinenza, completezza, verità della pagina o resistenza universale alle istruzioni malevole. L'interfaccia dice «Sintesi da verificare» e presenta ogni passaggio originale. `accepted_pending_semantic_review` e `qualityVerdict: pending_review` distinguono accettazione tecnica e qualità. Un risultato vuoto è astensione, non prova di assenza del dato in altre fonti. Output rifiutato: nessun testo del modello esposto e nessuna rigenerazione automatica.

I tempi di lettura e di generazione/controlli sono separati; non rappresentano il tempo esatto di disegno dello schermo. Una risposta corretta in un caso non certifica gli altri.

## Verifiche di sviluppo

104 test Python selezionati: nuove protezioni, lettura/cancellazione, contratto della sintesi, isolamento delle route, installer con rollback, ricerche preesistenti, memoria e runtime delle note. 13 test frontend (pagina web e memoria): richieste esplicite, payload minimali, escaping, passaggi visibili e output rifiutato nascosto. Vite bundle riuscito. Il TypeScript nativo installato nel container non è utilizzabile per il controllo completo; `tsc -b && vite build` va confermato sul Mac. Non è stato eseguito il modello del Mac in questo ambiente né un collaudo del suo browser.

Fonti tecniche consultate: upstream `src/openjarvis/tools/web_search.py`, `tests/tools/test_web_search.py`, `src/openjarvis/security/ssrf.py`, `tests/security/test_ssrf.py`; documentazione ufficiale Python `ssl` e `http.client`. Riutilizzato il pattern locale di processo cancellabile e il percorso già configurato del modello; nessun abilitamento indiscriminato degli strumenti upstream.

## Collaudo Mac finito

1. Build completa e visualizzazione dei pulsanti.
2. Lettura di una pagina pubblica di documentazione, confronto del testo estratto con la fonte.
3. Una sintesi della stessa pagina: controlli tecnici e revisione del significato separati; riportare risposta, passaggi e tempi.
4. Una domanda su un dato non presente nell'estratto: niente numero o verifica esterna inventati. Il risultato resta da valutare manualmente.
5. Interruzione durante lettura o sintesi: messaggio comprensibile e successiva operazione disponibile. Le verifiche di sviluppo sul processo non sono un'osservazione diretta del traffico Mac.

Non avanzare ad altri task se emerge un difetto in questo flusso. Conservare errori ed esiti, senza modificare criteri per dichiarare un test superato.

## Esito Mac della prima versione — 2026-10-04

Installer eseguito: quattro file, backup `20261004-233337-ncsmaylk`. Build completa `tsc -b && vite build` riuscita, 1,32 secondi per Vite. Pulsanti osservati nel browser.

| Controllo | Osservazione | Esito circoscritto |
| --- | --- | --- |
| Lettura documentazione Python asyncio | Fonte HTTPS ufficiale, 1721 ms, zero reindirizzamenti, testo mostrato | Superato per questa pagina |
| Sintesi di definizione e utilizzo | Due punti in italiano coerenti con i due passaggi inglesi originali mostrati; 50056 ms per generazione e controlli | Superato dopo revisione del significato di questa risposta |
| Domanda sulla RAM del Mac | Il modello si astiene, nessun valore inventato; 19785 ms | Superato per questo dato assente |
| Interruzione dal browser | Messaggio previsto dopo il clic; nessun nuovo errore dopo l'ultimo avvio nel log allegato | Superato per il feedback osservato; lo screenshot non certifica tutto il traffico o il rilascio del modello |
| Nuova operazione dopo l'interruzione | Nuova lettura visibile alle 23:52:42 | Superato per la disponibilità successiva |

Lettura e sintesi sono operative nei casi osservati. Le durate delle due sintesi riguardano domande e output differenti: non costituiscono un confronto di velocità. Non è noto quanto incidessero caricamento, contesto e generazione in quei due campioni.

Difetti emersi e conservati: testo con navigazione Sphinx residua; risultato sotto le schede senza spostamento automatico, percepito come nessun cambiamento; sintesi di circa 50 secondi. L'interruzione della sola lettura era troppo rapida per il clic iniziale: non viene riclassificata come un test eseguito sulla base della sua rapidità.

## Miglioramenti preparati dopo il collaudo

L'estrattore preferisce `<main>` o `role="main"` e rimuove i contenitori marcati come navigazione, sidebar, footer e relativi ruoli. In assenza di main conserva il testo generico filtrato. Mantiene titoli di articolo nel contenuto principale e non taglia a 6000 caratteri prima di selezionarlo. Un main senza testo utile produce un errore, senza sostituirlo con menu esterni. Il testo semplice conserva il percorso precedente. È comunque una selezione di HTML: CSS, markup errato e convenzioni dei siti possono lasciare rumore o omettere contenuto.

Dopo lettura, sintesi o errore l'interfaccia porta l'esito in vista e gli dà focus senza animazione. La verifica di questo comportamento nel browser Mac è ancora da fare.

Le misure della stessa inferenza separano primo JSON non mostrato, durata dello stream e sua chiusura, controlli, caratteri dell'estratto e dell'output. Il callback numerico Ollama già installato fornisce caricamento, elaborazione del contesto, generazione e conteggi dei token quando arriva il frame finale. Nessuna richiesta diagnostica aggiuntiva, nessuna stima dei campi mancanti, nessun testo salvato nelle misure. Le durate del modello e del backend si sovrappongono: non si sommano.

Non cambiano modello, quantizzazione, limiti di token, controlli delle citazioni, timeout o numero di generazioni. La pulizia può ridurre il contesto: il beneficio di latenza deve essere misurato sul Mac, non dedotto dai test con stream simulati.

Verifiche di questa revisione: 137 controlli Python selezionati, compresi installer precedente e nuovo, rollback e isolamento, estrazione con struttura Sphinx, dati numerici e callback nativo, interruzioni, memoria e runtime delle note; 15 controlli frontend; bundle Vite riuscito. I test frontend verificano richieste e rendering statico: non certificano scroll/focus sul Mac. Il nuovo controllo TypeScript completo resta da eseguire sul Mac per il limite del container già descritto. Consultati nuovamente i test upstream e il template ufficiale Sphinx `sphinx/themes/basic/layout.html`, che marca il contenuto con `role="main"`, oltre alla documentazione HTMLParser, scrollIntoView e Ollama chat.

Collaudo finito della revisione: una nuova lettura della stessa pagina per controllare visibilità e assenza dei menu estranei; una sintesi con la stessa domanda su definizione/utilità, revisione dei punti e raccolta delle fasi della richiesta. Non dichiarare migliorata la latenza se il nuovo campione non lo dimostra; niente ripetizioni automatiche.

## Distribuzione

Sorgenti: `b9677f739dcee2ddca9c7ec40a042128dfd122c2` sul branch `feature/andrea-local-profile`, PR #1 draft. Installer: `scripts/andrea/update_web_pages.py`, quattro file applicativi e controlli sulle dipendenze applicative precedenti, senza nuove dipendenze Python/npm. SHA-256 installer: `4d6b900238873cf953211d5ad0e2ba80e759c474dd9146e9b318637aca710fe6`. Richiede OpenJarvis fermo sulla porta 8008; nessun processo è terminato automaticamente.

Correzione interruzione browser: 5fb57e93630fecb5c5aefe2998d89bccd7f61bb8. Il log Mac mostrava CancelledError propagato ad ASGI dopo il pulsante Interrompi. Il runtime ora termina normalmente la richiesta scollegata dopo la pulizia dei task; una cancellazione richiesta al task dal server resta propagata. Tre test aggiunti: interruzione ricerca con worker terminato e successiva richiesta riuscita, interruzione delle due nuove route, cancellazione server conservata.
