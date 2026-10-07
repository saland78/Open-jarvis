# Ricerca web — valutazione del collegamento, modulo non ancora installato

## Stato verificato e scelta circoscritta

Branch personale verificato al commit `bdc07e63ac4453975e8f0931c659c699004f588e` prima del lavoro. Memoria esplicita collaudata; PR draft, nessuna unione a main. Upstream consultato al commit `a0df94cd93756047c724d803662bc671618b10d4`: `src/openjarvis/tools/web_search.py`, `tests/tools/test_web_search.py`, `tests/agents/test_hybrid_provider_search_security.py`. I test coprono motori espliciti, formato dei risultati, errori/fallback, URL e confine delle capacità di rete. Non certificano risultati di ricerca reali o significato delle sintesi.

Il componente upstream propone un endpoint You.com senza chiave e degrada automaticamente a DuckDuckGo in caso di errore. La [documentazione attuale dell'autenticazione](https://you.com/docs/using-the-api/authentication) presenta le REST API con chiave e il profilo MCP gratuito come percorso di valutazione senza chiave. La [guida MCP](https://you.com/docs/agents/mcp-server) documenta il profilo free e la restrizione per nome dello strumento. Non adottare implicitamente il vecchio endpoint o un cambio di fornitore. Il profilo gratuito è da valutare; non assumere che costituisca un contratto stabile per produzione, né introdurre credenziali o pagamenti.

Per questa prova viene scelto esplicitamente `https://api.you.com/mcp?profile=free&tools=you-search`. Nessuna risoluzione da variabili d'ambiente, chiave, pagamento, cookie persistente, proxy o redirect. Nessun fallback, retry o esecuzione di strumenti diversi da ricerca. Il protocollo HTTP/SSE segue la [specifica MCP 2025-03-26](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports): inizializzazione, notifica initialized, elenco strumenti e chiamate di ricerca. Se versione negoziata, schema o risultato non corrispondono al contratto supportato, fermarsi e riportare un errore; non trattare formati sconosciuti come assenza di risultati.

## Prova finita prima dell'interfaccia

`scripts/andrea/web_provider_probe.py` è autonomo e usa soltanto la libreria standard Python. Non richiede installazione, lettura del progetto o server OpenJarvis. Non legge note, memoria, conversazioni o configurazioni personali e non usa Ollama. Non modifica file. Si scarica separatamente in `/tmp` e si esegue dal Terminale Controlli, lasciando OpenJarvis aperto.

Due query fisse di documentazione pubblica: `site:docs.python.org asyncio wait_for` e `site:docs.ollama.com keep_alive`. Non accetta query personalizzate o percorsi. Mostra al massimo tre risultati per caso, titolo e testo limitati, URL HTTPS pubblici sintatticamente controllati, istante UTC e durata. Gli URL risultanti non vengono aperti o risolti: il controllo sintattico non certifica DNS o affidabilità del sito. Si riutilizza il contratto web/news dell'upstream per i campi dei risultati, senza chiamare l'esecutore generico o estrarre una presunta risposta da testo libero.

Il processo figlio ha un limite complessivo di 45 secondi, incluso DNS, connessione, lettura e protocollo. Ogni apertura ha timeout di 8 secondi, risposte limitate a 1 MiB. Un risultato JSON-RPC completo può chiudere la lettura SSE senza aspettare indefinitamente la fine della connessione. Scadenza o interruzione terminano il figlio e conservano i risultati già raccolti. Errori HTTP/di protocollo sono codificati senza stampare header, ID di sessione o corpo dell'errore del fornitore. Il numero di chiamate di ricerca tentate è distinto dai risultati raccolti.

I testi delle fonti restano dati letterali. Nessun testo remoto raggiunge un modello o un esecutore di comandi nella prova. `qualityVerdict=pending_review`, anche con dominio atteso trovato: rivedere pertinenza, collegamenti e limiti. Il flag del dominio è un controllo del collegamento riportato, non una verifica del contenuto della pagina.

## Verifiche e criteri prima della raccolta reale

Undici controlli di sviluppo passati: frammentazione SSE/CRLF/Unicode e notifiche non eseguite; JSON-RPC con ID esatto; dati duplicati, troppo grandi, incompleti o in errore; endpoint, query, sessione e assenza di autenticazione; schema/versione non supportati; deduplicazione e limiti; URL non pubblici o eseguibili; istruzioni ostili mantenute come testo; fallimento conservato senza retry; formati sconosciuti distinti da vuoto; scadenza/interruzione con terminazione del figlio. Simulatore, non intera suite upstream.

Avvio del diagnostico nel contenitore: procedura eseguita e arrestata prima di qualsiasi ricerca con `network_or_timeout`, zero query tentate. La raggiungibilità You.com dal contenitore non è verificata. Non riclassificare questo esito come successo o presumere lo stesso esito sul Mac.

La prova Mac deve concludere il protocollo e le due ricerche senza retry e mostrare risultati pertinenti con collegamenti delle rispettive documentazioni ufficiali. Se il fornitore blocca, limita, non risponde o cambia formato, il prerequisito non è superato; analizzare il motivo prima di integrarlo. Non ripetere fino al successo e non cambiare il fornitore silenziosamente. Nessuna ricerca reale sul Mac ancora eseguita.

## Passo di integrazione successivo

Dopo un esito reale favorevole, progettare una pagina locale Ricerca web con query esplicita mostrata prima dell'invio, fornitore nominato, risultati con collegamenti e data di consultazione. Nessun trasferimento automatico di memoria, vault o cronologia; indipendenza dai moduli locali. Lettura delle pagine e sintesi con citazioni richiedono budget propri e test di fonti discordanti, assenza, timeout e istruzioni ostili, mantenendo separati trasporto, formato e significato. Ricerca automatica nella chat, confronto Amazon e azioni sui siti non sono abilitate da questa valutazione.
