# Passaggi brevi con contesto — 2026-10-02

## Decisione e ambito

La proposta di sintesi libera breve del 2026-10-01 resta ritirata: il controllo reale aveva trasformato una fotografia storica in una scadenza. La nuova alternativa è esplicitamente estrattiva, con il pulsante **Passaggi brevi dalle fonti**. Il pulsante **Sintesi del modello** conserva il percorso precedente e i suoi limiti. Non si dichiara risolto il problema generale della correttezza delle parafrasi del modello.

brief.py seleziona il primo paragrafo utilizzabile di ogni estratto, con le intestazioni che lo precedono, e lo riporta tra virgolette con la fonte. Mantiene al massimo un passaggio di 140 parole per ciascuna delle tre fonti; non cancella parole per rispettare il limite. Testo troppo lungo, visibilmente troncato o con citazioni interne ambigue viene rifiutato con invito a leggere la nota. Le intestazioni vengono accostate al paragrafo conservandone testo e ordine; il layout delle righe vuote può cambiare. Nessuna data, quantità, qualifica o negazione viene parafrasata. modifiedAt non fornisce un periodo e non decide fra fonti discordanti.

È una selezione parziale, non una risposta esaustiva né un certificato della verità delle note. Il primo passaggio può non rispondere a una domanda specifica e il controllo di punteggiatura non dimostra che l'estratto contenga ogni qualifica della nota intera. La lunghezza dipende dal contesto necessario; non viene promesso un limite di 60 parole o due frasi. Una selezione letterale non equivale a una nuova sintesi generativa riuscita.

La richiesta notes_brief deve essere booleana e accompagnata da notes_query. Il backend rilegge le fonti dal vault, conserva i controlli su stati e scansioni parziali, invia le stesse evidenze SSE e termina lo stream con stop. answerMode è brief_quotes, inferenceUsed è false e le misure di generazione restano null. La chat e la sintesi libera mantengono messaggi, modello e budget precedenti; non si riattiva la guida di stile ritirata. Frontend e tipo ChatRequest distinguono le modalità e mostrano il limite della selezione.

## Consultazione upstream

Consultati tests/evals/scorers/test_doc_qa.py e src/openjarvis/evals/scorers/doc_qa.py di open-jarvis/OpenJarvis al commit c4da16e1ca3d21f4cc1905d4200063e564104f0f. Si conserva la separazione fra copertura dei fatti, citazioni e revisione del significato. Il confronto lessicale del verificatore upstream non prova la correttezza temporale: non viene usato come certificatore della parafrasi né viene introdotto un giudice cloud. Il parser scalare Obsidian upstream resta usato in isolamento dai test dell'adattatore. Nessuna intera suite upstream o backend Rust completo dichiarata eseguita.

## Verifica in sviluppo

67 verifiche tecniche mirate superate: 55 precedenti, 11 su estrazione e confini ASGI, una sul client della nuova suite. Sono coperti fotografie storiche, non verificato nella nota, negazioni, opinioni attribuite, fonti discordanti, limiti di lunghezza, testo tagliato, citazioni ambigue, richiesta non valida, bozze e scansione parziale. Il prompt della sintesi libera rimane invariato.

collaudo.py brief usa sette casi nuovi, distinti dai sei casi quality che rimangono invariati. I sette casi sono stati inviati via HTTP al LocalMode effettivo, con vault sintetico, ponte HTTP di sviluppo e inferenza simulata per gli altri percorsi: tutti completati, citazioni previste presenti, nessuna generazione invocata. Revisione separata dei testi rispetto ai criteri preregistrati:

| Caso | Esito | Controllo del significato |
|---|---|---|
| temporal_current | Superato | Data corrente e non verificato nella nota nello stesso blocco; nessuna scadenza o fusione con il blocco storico. |
| historical_snapshot | Superato | Data della fotografia e assenza storica riportate insieme, senza scadenza introdotta. |
| current_unknown | Superato | Qualifica nella nota, periodo e dato mancante diverso da zero conservati. |
| source_conflict | Superato | Entrambi i valori e le fonti; nessuna scelta dalla data del file. |
| resolved_problem | Superato | Risoluzione passata e mancanza di verifiche successive conservate. |
| attributed_opinion | Superato | Dichiarazione del relatore e limite di verifica restano nel passaggio. |
| cut_excerpt | Superato | Testo troncato rifiutato senza completamento inventato. |

qualityVerdict nel client resta pending_review: i controlli formali non approvano il significato automaticamente. Le risposte di questa tabella sono esclusivamente sintetiche; nessuna nota personale è riprodotta.

Il controllo TypeScript è passato con il compilatore JavaScript 5.9.3 nel solo ambiente di sviluppo, perché il compilatore nativo 7 del progetto richiede /proc/self/exe non disponibile nel contenitore. Il bundling Vite della modalità locale è passato; per completare la generazione PWA nel contenitore è usata la modalità development di Workbox nella sola copia di build. Questi adattamenti non sono pubblicati e non cambiano le dipendenze del Mac. La build standard sul Mac resta da verificare. Il browser di sviluppo non è stato collaudato: il download di Chromium disponibile all'ambiente non è riuscito. Il collaudo reale dell'interfaccia resta necessario.

## Aggiornamento e collaudo Mac finito

L'aggiornamento modifica soltanto sorgenti, test e questo documento, con commit fissato, SHA-256, baseline, backup e rollback. Non modifica vault, database, profili, dipendenze, modello o Jarvis originale. L'ottimizzazione della ricerca resta attiva.

**Collaudo previsto concluso e superato sul Mac il 2026-10-02 (Europe/Rome), per la modalità Passaggi brevi dalle fonti.**

L'aggiornamento ha applicato nove file da a07ae299d03fc8d8a8bedb85a8b313ca8cda5361 con hash dello script confermato e backup creato. Riavvio e build standard del Mac sono riusciti, inclusi TypeScript, Vite e generazione PWA; gli avvisi sui chunk e sugli import dinamici non hanno impedito il completamento. Nessuna dipendenza è stata aggiornata dallo script.

Il client brief sul Mac ha raccolto tutti e sette i casi, completati con finishReason stop, tutte le verifiche formali vere, answerMode brief_quotes e inferenceUsed false. I testi coincidono con i passaggi sintetici già rivisti secondo i criteri della tabella. La revisione semantica è quindi superata per questi sette casi; qualityVerdict rimane pending_review nel raccoglitore, senza attribuirgli un giudizio automatico.

Nel browser del Mac il nuovo pulsante è stato usato sulla stessa ricerca e sulla fonte reale prevista. Il passaggio selezionato coincide con il blocco corrente, conserva data dichiarata, limiti di verifica nella nota, negazioni e distinzione dalla fotografia storica. Non introduce scadenze né fonde il blocco storico con quello corrente; citazione e file/righe della fonte sono presenti. Screenshot, testi personali e log integrali non vengono pubblicati.

Questo chiude l'aggiornamento e il suo collaudo finito. Non trasforma in superato il precedente test negativo della sintesi generativa breve, non certifica tutti i passaggi del vault o ogni domanda e non verifica dashboard o report esterni. La sintesi libera resta separata e da verificare. Non sono richieste nuove misure Ollama per questo percorso senza inferenza; non si attribuisce un miglioramento alla generazione del modello.

PR draft, non unire a main. Memoria salvata non significa addestramento o apprendimento verificato.
