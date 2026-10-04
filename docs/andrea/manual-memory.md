# Memoria esplicita e correzioni — primo modulo

Stato al 2026-10-04: installazione sul Mac e build standard riuscite. Creazione, correzione, persistenza dopo riavvio ed eliminazione osservate nel browser. La risposta successiva alla correzione usa il valore nuovo; dopo l'eliminazione una nuova chat dichiara di non conoscere il valore. **Modulo ancora non concluso:** la prima risposta riportava il valore corretto ma attribuiva la scelta all'assistente con una formulazione in prima persona. Questo esito negativo resta conservato; non è annullato dalle prove successive. Vedi il [controllo circoscritto dell'attribuzione](memory-attribution-2026-10-04.md).

## Contratto

La pagina **Memoria e correzioni**, nel menu locale, consente di creare, leggere, modificare e cancellare preferenze, fatti dichiarati e correzioni. Il salvataggio richiede un'azione esplicita dell'utente. Le nuove voci sono inattive finché l'utente seleziona **Usa nelle chat**. Non viene letta la banca dati né estratta memoria dalle conversazioni.

Le voci attive sono inviate tutte, in modo deterministico, come contesto dichiarato in ogni richiesta della chat normale a Ollama locale. Un solo messaggio system conserva il prompt del profilo, oppure i prompt system già forniti dal chiamante; un messaggio user separato contiene il JSON letterale delle dichiarazioni salvate, seguito dalla conversazione originale. Non si riscrivono i pronomi o i soggetti nel testo salvato. Non si usa una ricerca semantica né una seconda inferenza. Nessuna memoria viene aggiunta alle richieste sulle note Obsidian, alle sintesi strutturate o ai loro schemi e validatori. Il modello e i limiti di produzione restano gli stessi. Nessun nuovo strumento o permesso viene concesso.

Se è stato fornito questo contesto e il modello termina normalmente una risposta non vuota, il programma aggiunge un avviso in coda alla risposta: memoria dichiarata fornita, nessuna verifica esterna. L'avviso è identificato come testo del programma; non certifica che il modello abbia usato ogni voce o che la risposta sia corretta. Non compare prima del primo testo del modello, sulle note, con memoria vuota/inattiva, o per un flusso vuoto, troncato o in errore. Non è una modifica alle affermazioni generate. Le misure del backend analizzano i frame originali del modello, senza contare l'avviso come primo testo o token generato; due flag senza contenuto indicano contesto fornito e avviso aggiunto.

Ogni voce ha ID stabile, argomento, testo, tipo, scelta di utilizzo e date di creazione/modifica. Il salvataggio conserva una revisione globale: una finestra con revisione superata riceve 409, senza sovrascrivere il nuovo contenuto. La pagina conserva la bozza e richiede ricaricamento/confronto. Modificare una voce conserva il suo ID e sostituisce il vecchio testo per le richieste successive. Non si conserva automaticamente lo storico delle versioni.

Limiti: 100 voci salvate; massimo 8 attive; massimo 2400 caratteri nel JSON complessivo delle voci attive, inclusi ID e nomi dei campi. Argomento massimo 80 caratteri, testo massimo 500. Non si elimina o tronca una voce per rispettare i limiti: si rifiuta la modifica e l'utente sceglie cosa disattivare. Un argomento normalizzato può avere soltanto una voce attiva. Non è un rilevatore generale di contraddizioni: argomenti differenti possono ancora contenere fatti incompatibili.

La provenienza è sempre **dichiarazione dell'utente**, senza verifica esterna. Salvare una correzione non cambia i pesi o gli algoritmi del modello e non dimostra che la applichi. Il modello può sbagliare anche con la memoria presente. Le istruzioni contenute nel contesto non autorizzano azioni; le API del profilo continuano a bloccare gli strumenti e le altre mutazioni.

## Dati locali e cancellazione

Il nuovo archivio è `~/.openjarvis-andrea/manual-memory.json`, distinto dai database upstream, dal vault e dal Jarvis originale. Nessuna migrazione o copia di quei dati. File e lock sono privati (0600 per i nuovi file); directory nuova 0700. Non è cifratura. Il modello locale riceve soltanto le voci attive; nessun servizio remoto riceve questo archivio attraverso il modulo.

Le scritture ricaricano lo stato sotto lock POSIX tra processi, scrivono un file temporaneo univoco, effettuano flush/fsync del file e sostituzione atomica. I lettori vedono una versione coerente vecchia o nuova. Nessuna garanzia contro ogni guasto del disco o perdita di alimentazione. Contenuto corrotto, link simbolici/hardlink o file non regolari producono un errore senza recupero silenzioso, senza usare i dati e senza sovrascriverli. Conservare il file per il recupero.

L'eliminazione richiede un secondo pulsante di conferma. Rimuove la voce dal nuovo archivio e dalle richieste future. Non è cancellazione forense: backup manuali, una richiesta già elaborata, il contesto temporaneo del motore e le conversazioni conservate dal browser sono elementi separati. Per verificare una correzione o cancellazione si usa una **nuova chat**, senza risposte precedenti nello storico. Non salvare credenziali in memoria.

GET/HEAD `/api/andrea/memory` legge lo stato senza cache; POST con JSON e origine locale compie una singola azione create/update/delete. L'host e l'origine sono validati dal confine già in uso; una richiesta esterna, senza origine o su API generiche non ottiene permessi. Durante una risposta si rifiutano le mutazioni. La lettura vuota non crea dati personali.

## Riutilizzo upstream e verifiche

Prima di scrivere codice: branch e PR verificati al commit `2f08b22f1fabc084422565023edf27aec208acb5`, PR #1 draft e non unita. Consultato OpenJarvis al commit `a0df94cd93756047c724d803662bc671618b10d4`:

- [FactStore e lock/replace](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/src/openjarvis/memory/store.py) e [test di persistenza, concorrenza, cancellazione e provenienza](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/memory/test_fact_store.py).
- [MemoryService](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/src/openjarvis/memory/service.py), relativi test e [MemoryManageTool](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/src/openjarvis/tools/memory_manage.py).
- [Backend SQLite](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/src/openjarvis/tools/storage/sqlite.py), [test SQLite](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/memory/test_sqlite.py), documentazione dell'architettura e test frontend dell'API memoria.

Si adattano i principi del FactStore: ricaricamento sotto lock e sostituzione atomica. È un archivio dedicato, non un'attivazione del servizio upstream. Il suo FactStore non offre modifica/cancellazione individuale con ID e revisione; il tool testuale può eliminare più righe per sottostringa. Il backend di indicizzazione non serve per otto voci esplicitamente attive. L'estrazione in background e gli strumenti generici restano disattivati. Nessuna dipendenza aggiunta.

Controlli dello store e del confine ASGI: persistenza tra istanze; correzione con ID conservato; eliminazione non risorta; revisioni superate; concorrenza tra processi; file corrotti e collegamenti; limiti senza cancellazione silenziosa; richieste esterne; assenza di inferenze nel CRUD; contenuto consegnato alla chat prima/dopo una correzione e dopo la cancellazione; note senza memoria aggiunta. Il sink di test verifica il contesto consegnato, **non l'applicazione semantica da parte di un modello reale**.

Le prove storiche conservano il runtime precedente come archivio con gli hash originali; i diagnostici pubblicati non vengono modificati. Sistemato il test delle metriche native che usava un vecchio formato JSON nel simulatore: utilizza ora lo stesso output sintetico della prova di produzione, conservando l'uguaglianza della risposta e il controllo delle metriche.

Esito: 185 esecuzioni Python pertinenti superate (15 del nuovo modulo, regressioni dei confini e archivi), 17 verifiche frontend superate su tre file. Non è stata eseguita l'intera suite upstream. Nessuna nota personale o inferenza reale utilizzata.

Frontend: controlli su origine locale, contenuto/revisione inviati, errori senza retry e spiegazione del modulo. Typecheck con TypeScript JavaScript 5.9.3 disponibile nell'ambiente e build Vite 8.3.0 completati; il compilatore nativo TypeScript 7 locale non può leggere `/proc/self/exe` in questo ambiente. Sul Mac la build standard con la versione del lock installato è riuscita; rendering e azioni della pagina verificati nei casi descritti sotto.

## Serie Mac prevista e risultati

Aggiornamento: `scripts/andrea/update_manual_memory.py` scarica cinque sorgenti fissati al commit `07c8ce93b0e4c5d486b7a24b26c4763e77b1ae4e`, verificando baseline e SHA-256. Tutte le destinazioni sono controllate prima del primo download, poi ricontrollate prima di applicare i file. Porta 8008 libera richiesta; backup e rollback conservano i file precedenti. Non crea l'archivio della memoria, non modifica note, profilo, database o dipendenze. Il launcher ricompilerà la UI al successivo avvio perché sono cambiati i sorgenti; la normale preparazione della build usa le dipendenze già definite nel lock, senza cambiare le loro versioni.

Sette test dell'aggiornamento superati: manifest effettivo, backup e ripetizione; download errato; modifiche locali; porta occupata senza terminare processi; rollback con rimozione dei nuovi file; file nuovi incompatibili/collegamenti; modifica durante il download. File privati sintetici conservati in tutte queste prove. Sul Mac l'aggiornamento di cinque file è riuscito; build standard TypeScript/Vite/PWA e interazione con la pagina confermate. Nessun nuovo dato personale pubblicato.

Usare soltanto dati sintetici. Nessun caricamento del vault o benchmark ripetuto fino al successo.

1. Aprire **Memoria e correzioni**. Creare un fatto dichiarato con argomento `Colore test`, testo `Per il progetto sintetico Zefiro il colore scelto è verde.`, attivando **Usa nelle chat**. Ricaricare: voce, stato e testo devono coincidere.
2. In una nuova chat chiedere `Quale colore ho scelto per il progetto sintetico Zefiro?`. La risposta deve riportare verde come dichiarazione, senza inventare una verifica o azione.
3. Modificare la stessa voce in tipo **Correzione**, testo `Per il progetto sintetico Zefiro il colore scelto è blu.`. In un'altra nuova chat ripetere la domanda: deve rispondere blu, senza conservare verde come scelta attuale.
4. Fermare/riavviare soltanto OpenJarvis. Riaprire la pagina: la voce blu deve essere presente e attiva.
5. Eliminare la voce con conferma. In un'altra nuova chat ripetere la domanda: non deve attribuire un colore dalla memoria né inventare di averlo verificato. Ricaricare la pagina: voce assente.

Sono tre richieste al modello, senza retry automatici. Annotare risposte e tempi della UI, senza pubblicare contenuti personali. Se una richiesta non rispetta il criterio, conservarne l'esito e diagnosticare quel caso: salvataggio corretto e memoria applicata restano valutazioni distinte. Non passare al modulo successivo prima di rivedere questi esiti.

Esiti osservati: primo richiamo **non completamente superato** per attribuzione errata; secondo richiamo dopo la correzione superato nel caso osservato; persistenza dopo riavvio confermata con voce attiva e revisione 2; eliminazione confermata con zero voci e revisione 3; terzo richiamo in nuova chat superato nel caso osservato, senza riproporre un valore cancellato o inventare una verifica. Questi esiti non dimostrano apprendimento del modello, affidabilità universale o cancellazione forense.
