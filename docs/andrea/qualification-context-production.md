# Istruzioni specializzate per le qualifiche della nota scelta

Stato al 2026-10-04: **aggiornamento di un file installato con backup, avvio e collaudo della nota reale superati**. I quattro fatti selezionati e la consultazione completa sono conservati; backend 19,489 s. Il tempo UI è escluso dai confronti perché la pagina segnala la scheda in secondo piano. Adozione chiusa nell’ambito osservato; nessuna ulteriore inferenza richiesta. Si adotta soltanto il messaggio system di 824 caratteri del percorso riconosciuto delle qualifiche. Nessuna modifica al modello, al budget, al messaggio user o alle fonti.

## Problema e comportamento

Il trasporto compatto già installato usava 1631 caratteri di istruzioni derivate dal contratto generale, comprese regole per libri e copertine che questo percorso non elabora. Il messaggio specializzato mantiene ambito della nota, qualifiche, numeri, date esplicite, separazione dei record e trattamento delle istruzioni nelle fonti come dati. Evita al modello istruzioni per un diverso tipo di sintesi.

La modifica è in [qualification_compact_wire.py](../../scripts/andrea/qualification_compact_wire.py). Sono invariati messaggio user, schema nativo con F1/F2/F4, copia dichiarata della frase F3 completa e delle date dei contesti, codice di validazione della risposta e rendering. Ogni stringa generata attraversa gli stessi controlli senza riscrittura. Il backend continua a rileggere la nota prima di accettare il risultato; un cambiamento di contenuto, stato o vault lo rifiuta. I percorsi per libri, ricerca generale, passaggi brevi e chat non cambiano.

Gli identificativi casuali della diagnosi **non** entrano in produzione. La normale cache di Ollama rimane disponibile; nessun unload, warm-up, retry, parametro globale o dipendenza viene introdotto.

## Evidenza disponibile

La [prima serie di quattro richieste](qualification-context-prompt-experiment.md#esito-mac-della-serie-finita--2026-10-04) conserva il proprio verdetto: revisione delle quattro risposte favorevole e meno token di input, soglia prestazionale originale **non superata** perché la cache rende il confronto del prefill non attribuibile. Non viene ripetuta o riclassificata.

La [diagnosi distinta di due richieste](qualification-prefill-isolation-diagnostic.md) isola quasi interamente il prompt nuovo. Criteri fissati prima della raccolta: massimo 8 token in cache, almeno 98% del prompt nuovo, almeno 20% di nuovi token e 15% di durata prefill in meno, oltre a quattro fatti e revisione separata delle risposte. Il [rapporto sintetico originale con revisione aggiunta](qualification-prefill-isolation-mac-2026-10-04.json) conserva tutti i verdetti tecnici iniziali.

| Misura nativa | Istruzioni precedenti | Istruzioni specializzate |
|---|---:|---:|
| Token totali del prompt | 715 | 523 |
| Token in cache | 0 | 3 |
| Token effettivamente elaborati | 715 | 520 |
| Copertura non in cache | 100% | 99,4264% |
| Durata elaborazione del prompt | 10626,631 ms | 7906,994 ms |
| Caricamento | 3816,363 ms | 1,933 ms |
| Durata generazione | 7692,708 ms | 5374,364 ms |
| Token generati | 72 | 53 |

Nuovi token **−27,273%**, prefill **−25,593%**: soglie della nuova diagnosi superate. Entrambe le risposte conservano conteggio, variabilità per periodo, frase corrente completa limitata alla nota, qualifica storica, date e citazioni. Nessuna verifica esterna inventata. Il genere grammaticale errato di “royalty” nella risposta precedente non cambia il fatto riportato.

Sono due richieste ordinate, non una stima statistica. Il caricamento differente impedisce di attribuire al solo prompt la differenza dei totali. La misura non dimostra vantaggio nella normale cache calda, primo testo accettato dal backend o latenza dell’interfaccia. Questi esiti rimangono distinti dal prefill. Una risposta futura può ancora avere errori di significato.

## Verifiche della produzione e dell’aggiornamento

**236 controlli Python pertinenti passati**, inclusi 6 nuovi sul confine ASGI e 7 sul manifest di un file. Payload di produzione identico alla candidata riesaminata, senza prefisso diagnostico; replay dei tre JSON candidati già osservati nelle due prove, senza nuove inferenze. I quattro fatti e gli estratti comprovati restano presenti. Rifiuti per chiavi mancanti o duplicate, numero/data/qualifica alterati, istruzioni o metadati cambiati, interruzione e nota modificata restano attivi. La dimostrazione di una negazione semanticamente opposta ma tecnicamente valida rimane `pending_review`: non si presenta il validator come certificazione del significato.

La vecchia versione dell’helper è archiviata byte per byte in `tests/fixtures/andrea/qualification_compact_wire_before_context.py`. I probe e gli installer precedenti conservano hash, protocolli e risultati; i test storici usano il loro archivio, senza allentare le verifiche del Mac. Dopo questa adozione i vecchi probe devono rifiutare la nuova installazione prima della rete. Nessuna nuova serie A/B serve alla chiusura.

Consultati prima dell’adozione i [test di output strutturato upstream](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_structured_output.py) e [test opzioni Ollama](https://github.com/open-jarvis/OpenJarvis/blob/a0df94cd93756047c724d803662bc671618b10d4/tests/engine/test_ollama_runtime_options.py). Si riusano formato nativo e opzioni già supportati dal motore; non si attivano gli altri servizi. Intera suite upstream non eseguita.

## Procedura di installazione e criteri di chiusura sul Mac

[update_qualification_context.py](../../scripts/andrea/update_qualification_context.py) scarica **un solo file da un commit preciso** e ne controlla hash e sintassi prima di applicarlo. Controlla 13 componenti immutabili; rifiuta modifiche locali incompatibili, symlink e porta 8008 occupata. Transazione, backup e ripristino riusati dall’installer precedente. Nessuna nota, configurazione, database, dipendenza, frontend o file del Jarvis originale viene sostituito.

Procedura usata, completata un passo alla volta:

1. Fermare solo il Terminale **OpenJarvis** con Control+C e attendere il prompt; lasciare **Controlli** aperto.
2. Nel Terminale **Controlli**, scaricare l’installer fissato a commit e verificare SHA-256; poi eseguirlo con il Python della venv del progetto. Attendere il risultato prima di proseguire.
3. Riavviare nel Terminale **OpenJarvis** con `bash Avvia-OpenJarvis.command` dalla cartella esistente; lasciare quel Terminale aperto.
4. Nel browser su `http://127.0.0.1:8008`, **Data Sources → Note Obsidian**, cercare la nota KPI e premere **Sintesi della nota** nella scheda del risultato scelto, una sola volta. Rivedere i quattro fatti e i loro passaggi originali; registrare esito tecnico e tempi visibili.
5. Se serve separare caricamento, contesto e generazione, leggere le metriche della stessa richiesta con il lettore già installato, senza emettere altre inferenze. Condividere soltanto l’output necessario, evitando cronologia del Terminale e dati personali.

Per chiudere questa adozione servono installazione riuscita, avvio, una sintesi reale accettata, quattro fatti conservati nel confronto con la fonte e tempi disponibili. Non si impone al singolo campione UI una riduzione che la diagnosi non ha certificato. Risultato reale e tempi vanno riportati anche se peggiori o non conclusivi; un difetto non viene ignorato per passare al modulo successivo. PR #1 sempre draft, senza merge.


## Collaudo reale concluso e superato — 2026-10-04

Installer e sorgente verificati per SHA-256, aggiornamento di un file e backup confermati dal Terminale; avvio e pagina aperta confermati. La risposta del percorso **Sintesi della nota** è completata e accettata. La revisione manuale confronta i quattro fatti con i passaggi originali: conteggio dichiarato, variabilità per periodo, frase corrente completa limitata alla nota con indicazioni di consultazione e qualifica storica distinta. Date, quattro citazioni e origini dichiarate conservate; nessuna deduzione di zero o verifica di sistemi esterni. Esito circoscritto ai fatti selezionati della nota reale, non alla verità esterna di tutta la nota.

Il [rapporto numerico filtrato](qualification-context-production-mac-2026-10-04.json) conserva separatamente la revisione, il lettore nativo invariato e l’osservazione UI. Nessun testo della nota, percorso privato, dato commerciale, screenshot, timestamp della nota, ID o storico del Terminale viene pubblicato.

| Fase della stessa richiesta | Tempo / conteggio |
|---|---:|
| Recupero nota nel backend | 3,25 ms |
| Caricamento Ollama | 5585,045 ms |
| Elaborazione del prompt | 8473,515 ms |
| Generazione del testo | 5365,669 ms |
| Controlli strutturati | 5,38 ms |
| Primo testo accettato dal backend | 19488,31 ms |
| Totale backend | 19488,63 ms |
| Token del prompt / in cache | 475 / 0 |
| Token generati | 53 |

Il lettore ha emesso **zero inferenze** e non ha letto il vault: le fasi provengono dalla stessa richiesta già in memoria. Primo frammento JSON a 14110,78 ms; non è testo accettato o visibile. Il riquadro del browser riporta primo contenuto a 19518 ms e aggiornamento UI a 19521 ms, ma segnala **scheda osservata in secondo piano**: conservare i valori e **escluderli dai confronti della latenza UI in primo piano**. La diagnosi sintetica precedente sul prefill mantiene il proprio esito; non diventa una certificazione dei tempi nel browser. Caricamento, input e output possono variare, quindi non si deduce un miglioramento causale o statistico universale dal singolo campione reale.

Il task di questa adozione è chiuso: diagnosi nuova con soglie prefissate superate, 236 controlli di sviluppo pertinenti, installazione, avvio, risposta reale accettata, revisione dei quattro fatti e tempi della stessa richiesta disponibili. Il precedente test confuso dalla cache conserva l’esito non superato e non viene ripetuto. Nessun test UI aggiuntivo è necessario per questo ambito: una futura valutazione quantitativa della latenza in primo piano richiede un task distinto e protocollo esplicito. Modello e protezioni restano quelli collaudati. La roadmap può proseguire dalla memoria e dalle correzioni; nessuna funzione successiva è attivata da questa chiusura. PR #1 draft, non unire.
