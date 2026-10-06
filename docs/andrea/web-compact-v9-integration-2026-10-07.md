# Collegamento della sintesi compatta all’app

Questa modifica collega il componente consolidato v9 a `web_page_context_contract`, usato da `LocalWebPages.summarize` e dalla API dell’interfaccia. Il problema operativo era continuare a provare varianti isolate mentre l’app conservava il vecchio contratto. Il contenuto dei messaggi, lo schema, la selezione e i controlli coincidono con il candidato compatto v9 già eseguito sul Mac; il collegamento non aggiunge nuove istruzioni al modello.

Il parser della pagina, la fonte integrale di audit, la domanda, il trasporto, il modello, le opzioni e i timeout restano quelli del percorso installato. La piccola estensione finita delle forme CSV rimane in una copia isolata del contratto di fedeltà. Il modulo viene caricato dalla posizione effettiva della dipendenza verificata: questo permette di verificarlo anche prima dell’installazione, con file distribuiti fra staging e progetto.

## Esiti e protocollo di chiusura

Il confronto storico v9 resta registrato con sei trasporti/forme corretti e cinque giudizi di significato favorevoli su sei. Il primo risultato del riferimento storico aggiunge un meccanismo non dimostrato dal proprio passaggio. Quella risposta non è corretta dal programma e non viene riclassificata favorevole. Il vecchio gate a sei risposte **rimane non superato**. Non è una misura della qualità del contratto attualmente installato, perché il riferimento era un prompt archiviato.

Le tre risposte del candidato compatto sono state giudicate favorevoli nel risultato v9, come nelle due serie precedenti di revisioni diverse. Questo sostiene il collegamento reversibile del candidato, non certifica qualunque risposta futura. Le riduzioni misurate nel v9 sono 15,470% per il prefill asyncio e 64,444% per il prefill CSV; non sono un confronto con il prompt corrente dell’app, una previsione statistica o una misura della pipeline vocale.

Il nuovo collaudo di integrazione è separato ed esplicito: due letture pubbliche e tre sintesi attraverso `/api/andrea/web/read` e `/api/andrea/web/summarize`, con le stesse tre domande. Deve usare la revisione `compact_web_evidence_v9`, produrre due punti asyncio, una regola CSV completa e un’astensione per il prezzo assente. Le risposte, i passaggi originali e i tempi restano nel report. Un’astensione sui due casi positivi non passa. Una revisione manuale deve confermare tutti e tre i significati; il programma lascia `qualityVerdict=pending_review`. Non contatta direttamente Ollama, non legge il vault e non ritenta il modello.

Il collaudo sull’app installata è ancora da eseguire. Il rendering nel browser e la latenza audio non sono misurati. Nessun altro task della roadmap viene chiuso da questa modifica.

## Verifica locale e aggiornamento

La suite pertinente comprende i 53 moduli web/risorse/trasporto già verificati e tre moduli nuovi: consolidamento, servizio reale e installer. Le vecchie prove di payload e risposte archiviate usano una copia esatta della facciata v1; i nuovi test usano la facciata v9 realmente collegata al servizio. Le vecchie aspettative non vengono rilassate per accettare output diversi.

Un tentativo aggiuntivo di discovery globale su 1241 test non è passato: 30 fallimenti e 29 errori, includendo fixture di vecchi aggiornamenti non compatibili con la versione corrente e processi avviati da stdin. Non lo presentiamo come un controllo globale superato. La suite web pertinente viene eseguita da un file con entry point protetto e documentata separatamente.

L’installer verifica baseline e SHA-256 di dodici file, importa lo staging prima di modificare il progetto, richiede la porta 8008 libera, crea un backup e ripristina i file se una sostituzione fallisce. Non modifica note, memoria, database, configurazione, frontend o dipendenze. Rifiuta modifiche locali inattese e collegamenti simbolici. La normale API del programma rimane la stessa.

Consultato il test primario OpenJarvis `tests/engine/test_structured_output.py`: utile per la propagazione del formato JSON/schema, non una certificazione del significato. La verifica della facciata include richieste singole, chiusura dello stream, rifiuto di `finish_reason=length`, verbi di controllo e astensione genuina.
